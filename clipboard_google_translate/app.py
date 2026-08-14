"""Tkinter UI wiring the clipboard watcher, translator and logger together.

Threading model
----------------
- ClipboardWatcher thread: polls the OS clipboard, never touches Tk.
- Translation worker thread: does the (slow, network-bound) translation
  calls, never touches Tk.
- Tk main thread: owns every widget. It feeds work to the worker thread via
  `_request_queue` and drains results from `_result_queue` on a
  `root.after` timer -- the only Tk-safe way to bring data back from
  another thread.

UI layout
---------
The main window only shows the input/output boxes and a status line, to
keep it out of the way. Every control (language, OCR toggle, log, etc.)
lives in a separate Settings window opened via the gear button.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import WORD, Button, Checkbutton, Label, OptionMenu, Text, Toplevel
from typing import NamedTuple, Optional

import pyperclip
from PIL import Image

from .clipboard_watcher import ClipboardWatcher
from .logger import TranslationLogger
from .ocr import OcrError, OcrService
from .settings import AppSettings
from .text_utils import has_visible_text, reflow_sentences, remove_newlines
from .translator import TranslationError, TranslationService

RESULT_POLL_MS = 50
EDIT_POLL_MS = 300
LANGUAGES = (("VI", "vi"), ("JA", "ja"), ("EN", "en"))
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 28


class TranslationRequest(NamedTuple):
    """Either `source_text` or `image` is set -- an image is OCR'd into
    source_text by the worker thread before translation."""

    source_text: Optional[str] = None
    image: Optional[Image.Image] = None


@dataclass
class TranslationResult:
    source_text: str
    translated_text: Optional[str]
    error: Optional[str] = None


@dataclass(frozen=True)
class _TextSnapshot:
    """A recorded state of both boxes, for the app-level Undo/Redo.

    Tk's own Text-widget undo (`-undo`) records every insert/delete, so
    toggling it off around a programmatic overwrite to keep that overwrite
    out of the undo stack corrupts the stack instead (verified: undo lands
    on stale/empty text, redo reconstructs a state that never existed).
    A simple linear history of whole-box snapshots, pushed only after each
    complete action (a translation landing, Clear, Auto Fix), avoids that
    entirely and matches "step through past states," not "replay
    keystrokes."
    """

    input_text: str
    output_text: str


class TranslatorApp:
    def __init__(self) -> None:
        self.root = tk.Tk()

        self.translator = TranslationService()
        self.logger = TranslationLogger()
        self.ocr = OcrService()

        settings = AppSettings.load()

        self._dest_lang = settings.dest_lang
        self._font_size = settings.font_size
        self._last_source = ""
        self._last_result = ""
        self._last_input_seen = ""
        self._settings_window: Optional[Toplevel] = None

        # Plain values, not tk.Variables: the watcher/worker threads read
        # these flags, and Tk variables -- like widgets -- aren't
        # thread-safe. The matching `*_var` is the checkbox's own display
        # state; `_poll_results` keeps it mirroring the plain flag on the
        # main thread.
        self._strip_pdf_newlines = True
        self._strip_pdf_newlines_var = tk.BooleanVar(value=True)
        self._ocr_enabled = settings.ocr_enabled
        self._ocr_enabled_var = tk.BooleanVar(value=settings.ocr_enabled)
        self._overwrite_clipboard = settings.overwrite_clipboard
        self._overwrite_clipboard_var = tk.BooleanVar(value=settings.overwrite_clipboard)

        self._busy_event = threading.Event()
        self._status_var = tk.StringVar()
        self._settings_saved_var = tk.StringVar()

        self._history: list[_TextSnapshot] = [_TextSnapshot("", "")]
        self._history_index = 0

        self._request_queue: "queue.Queue[Optional[TranslationRequest]]" = queue.Queue()
        self._result_queue: "queue.Queue[TranslationResult]" = queue.Queue()

        self._build_widgets()
        self.root.geometry(f"{settings.window_width}x{settings.window_height}")
        self._update_status()
        self._update_title()

        self._watcher = ClipboardWatcher(
            on_text_change=self._on_clipboard_text_change,
            on_image_change=self._on_clipboard_image_change,
        )
        self._worker = threading.Thread(
            target=self._translation_worker_loop, name="TranslationWorker", daemon=True
        )

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- UI construction -------------------------------------------------

    def _build_widgets(self) -> None:
        root = self.root

        # Three real columns -- left box / gutter / right box -- weighted
        # 49/2/49 so the split stays an even 50/50 with a visible gap as
        # the window resizes. (Spanning a widget across many dummy
        # columns, as the original layout did, makes Tk's grid split the
        # extra space unevenly -- a single real column per side is what
        # actually keeps both boxes the same width.)
        root.columnconfigure(0, weight=49)
        root.columnconfigure(1, weight=2, minsize=12)
        root.columnconfigure(2, weight=49)
        root.rowconfigure(1, weight=1)

        # One frame spanning all 3 columns, not just column 0 -- otherwise
        # the status text's width becomes column 0's minimum width and
        # throws off the 49/2/49 split versus column 2 (which only has
        # the short Copy_Result button).
        top_row = tk.Frame(root)
        top_row.grid(row=0, column=0, columnspan=3, sticky=tk.EW)

        left_group = tk.Frame(top_row)
        left_group.pack(side=tk.LEFT)
        Button(
            left_group, text="⚙ Settings", command=self._open_settings, font=("NSimSun", 11)
        ).pack(side=tk.LEFT, padx=(0, 8))
        Label(left_group, textvariable=self._status_var, font=("NSimSun", 11)).pack(side=tk.LEFT)

        icon_font = ("Segoe UI Symbol", 12)
        Button(
            top_row, text="🗐", command=self._copy_result_to_clipboard, font=icon_font, width=2
        ).pack(side=tk.RIGHT)
        Button(top_row, text="🧹", command=self._clear_all, font=icon_font, width=2).pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        Button(top_row, text="✎", command=self._auto_fix_text, font=icon_font, width=2).pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        Button(
            top_row, text="+", command=self._increase_font_size, font=("NSimSun", 11), width=2
        ).pack(side=tk.RIGHT, padx=(8, 0))
        Button(
            top_row, text="-", command=self._decrease_font_size, font=("NSimSun", 11), width=2
        ).pack(side=tk.RIGHT)
        Button(top_row, text="↻", command=self._redo, font=icon_font, width=2).pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        Button(top_row, text="↺", command=self._undo, font=icon_font, width=2).pack(
            side=tk.RIGHT, padx=(8, 0)
        )

        self.input_text = Text(width=35, height=15, wrap=WORD, font=("Arial", self._font_size))
        self.input_text.grid(row=1, column=0, pady=0, padx=0, sticky=tk.NSEW)

        self.output_text = Text(width=35, height=15, wrap=WORD, font=("Arial", self._font_size))
        self.output_text.grid(row=1, column=2, pady=0, padx=0, sticky=tk.NSEW)

    def _open_settings(self) -> None:
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.lift()
            self._settings_window.focus_force()
            return

        win = Toplevel(self.root)
        win.title("Settings")
        win.resizable(False, False)
        self._settings_window = win

        font = ("NSimSun", 11)
        pad = {"padx": 10, "pady": (10, 0), "sticky": tk.W}

        Label(win, text="Dest. language:", font=font).grid(row=0, column=0, **pad)
        lang_var = tk.StringVar(value=self._dest_lang)
        OptionMenu(win, lang_var, *(code for _, code in LANGUAGES), command=self._set_dest_lang).grid(
            row=0, column=1, padx=10, pady=(10, 0), sticky=tk.W
        )

        Checkbutton(
            win,
            text="Translate images (OCR)",
            variable=self._ocr_enabled_var,
            command=self._on_toggle_ocr_enabled,
            font=font,
        ).grid(row=1, column=0, columnspan=2, **pad)

        Checkbutton(
            win,
            text="REMOVE_ENTER",
            variable=self._strip_pdf_newlines_var,
            command=self._on_toggle_strip_newlines,
            font=font,
        ).grid(row=2, column=0, columnspan=2, **pad)

        Checkbutton(
            win,
            text="Overwrite clipboard with result",
            variable=self._overwrite_clipboard_var,
            command=self._on_toggle_overwrite_clipboard,
            font=font,
        ).grid(row=3, column=0, columnspan=2, **pad)

        Button(win, text="Save_Log", command=self._save_log, font=font).grid(row=4, column=0, **pad)
        Button(win, text="Open_Log", command=self.logger.open_folder, font=font).grid(
            row=4, column=1, **pad
        )

        self._settings_saved_var.set("")
        Button(win, text="Save Settings", command=self._save_settings, font=font).grid(
            row=5, column=0, **pad
        )
        Label(win, textvariable=self._settings_saved_var, font=font).grid(row=5, column=1, **pad)

        tk.Frame(win, height=10).grid(row=6, column=0)

    # ---- clipboard / edit -> translation request --------------------------

    def _on_clipboard_text_change(self, text: str) -> None:
        """Runs on the watcher thread. Must not touch Tk widgets."""
        if has_visible_text(text) and text != self._last_result:
            self._request_queue.put(TranslationRequest(source_text=text))

    def _on_clipboard_image_change(self, image: Image.Image) -> None:
        """Runs on the watcher thread. Must not touch Tk widgets."""
        if self._ocr_enabled:
            self._request_queue.put(TranslationRequest(image=image))

    def _poll_input_edits(self) -> None:
        current = self.input_text.get("1.0", "end-1c")
        if (
            current != self._last_input_seen
            and has_visible_text(current)
            and current != self._last_source
        ):
            self._last_input_seen = current
            self._request_queue.put(TranslationRequest(source_text=current))
        self.root.after(EDIT_POLL_MS, self._poll_input_edits)

    # ---- translation worker (background thread) ---------------------------

    def _translation_worker_loop(self) -> None:
        while True:
            request = self._request_queue.get()
            if request is None:  # shutdown sentinel
                return

            self._busy_event.set()
            try:
                self._handle_request(request)
            finally:
                self._busy_event.clear()

    def _handle_request(self, request: TranslationRequest) -> None:
        from_image = request.image is not None
        if from_image:
            try:
                source_text = self.ocr.recognize(request.image)
            except OcrError as exc:
                self._result_queue.put(TranslationResult("", None, error=f"OCR: {exc}"))
                return
            if not has_visible_text(source_text):
                return
        else:
            source_text = request.source_text

        if self._strip_pdf_newlines:
            source_text = remove_newlines(source_text)
            self._strip_pdf_newlines = False  # one-shot: applies to the next paste only
            if self._overwrite_clipboard:
                pyperclip.copy(source_text)
                self._watcher.mark_seen(source_text)

        try:
            translated = self.translator.translate_lines(source_text, self._dest_lang)
            self._result_queue.put(TranslationResult(source_text, translated))
        except TranslationError as exc:
            self._result_queue.put(TranslationResult(source_text, None, error=str(exc)))

    # ---- results -> UI (main thread) --------------------------------------

    def _poll_results(self) -> None:
        try:
            while True:
                result = self._result_queue.get_nowait()
                self._apply_result(result)
        except queue.Empty:
            pass
        # The worker thread may have auto-disabled the one-shot flag;
        # reflect that on the checkbox (main thread only touches the var).
        if self._strip_pdf_newlines_var.get() != self._strip_pdf_newlines:
            self._strip_pdf_newlines_var.set(self._strip_pdf_newlines)
        self._update_status()
        self.root.after(RESULT_POLL_MS, self._poll_results)

    def _apply_result(self, result: TranslationResult) -> None:
        if result.error is not None:
            self._set_text(self.output_text, f"[translation error] {result.error}")
            return

        self._set_text(self.input_text, result.source_text)
        self._last_input_seen = result.source_text
        self._set_text(self.output_text, result.translated_text or "")

        self._last_source = result.source_text
        self._last_result = result.translated_text or ""
        self._push_history()

        if self._overwrite_clipboard:
            pyperclip.copy(self._last_result)
            self._watcher.mark_seen(self._last_result)

        self.root.call("wm", "attributes", ".", "-topmost", "1")
        self.root.after_idle(self.root.call, "wm", "attributes", ".", "-topmost", False)

    @staticmethod
    def _set_text(widget: Text, text: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", text)

    # ---- settings actions --------------------------------------------------

    def _on_toggle_strip_newlines(self) -> None:
        self._strip_pdf_newlines = self._strip_pdf_newlines_var.get()

    def _on_toggle_ocr_enabled(self) -> None:
        self._ocr_enabled = self._ocr_enabled_var.get()
        self._update_status()

    def _on_toggle_overwrite_clipboard(self) -> None:
        self._overwrite_clipboard = self._overwrite_clipboard_var.get()

    def _set_dest_lang(self, lang_code: str) -> None:
        self._dest_lang = lang_code
        self._update_title()
        self._update_status()
        current = self.input_text.get("1.0", "end-1c")
        if has_visible_text(current):
            self._request_queue.put(TranslationRequest(source_text=current))

    def _copy_result_to_clipboard(self) -> None:
        pyperclip.copy(self._last_result)
        self._watcher.mark_seen(self._last_result)

    def _clear_all(self) -> None:
        self.input_text.delete("1.0", "end")
        self.output_text.delete("1.0", "end")
        self._last_input_seen = ""
        self._push_history()

    def _auto_fix_text(self) -> None:
        """Drop line breaks and re-split on sentence punctuation, in both boxes."""
        new_input = reflow_sentences(self.input_text.get("1.0", "end-1c"))
        new_output = reflow_sentences(self.output_text.get("1.0", "end-1c"))
        self._set_text(self.input_text, new_input)
        self._set_text(self.output_text, new_output)
        # Treat this as already "seen" so it doesn't itself trigger a
        # fresh translation request -- it's a formatting pass, not an edit.
        self._last_input_seen = new_input
        self._push_history()

    # ---- undo/redo (app-level history, see _TextSnapshot) -----------------

    def _push_history(self) -> None:
        snapshot = _TextSnapshot(
            self.input_text.get("1.0", "end-1c"),
            self.output_text.get("1.0", "end-1c"),
        )
        if snapshot == self._history[self._history_index]:
            return
        del self._history[self._history_index + 1 :]  # drop the stale redo branch
        self._history.append(snapshot)
        self._history_index = len(self._history) - 1

    def _restore_snapshot(self, snapshot: _TextSnapshot) -> None:
        self._set_text(self.input_text, snapshot.input_text)
        self._set_text(self.output_text, snapshot.output_text)
        self._last_input_seen = snapshot.input_text
        self._last_source = snapshot.input_text
        self._last_result = snapshot.output_text

    def _undo(self) -> None:
        if self._history_index > 0:
            self._history_index -= 1
            self._restore_snapshot(self._history[self._history_index])

    def _redo(self) -> None:
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self._restore_snapshot(self._history[self._history_index])

    def _increase_font_size(self) -> None:
        self._set_font_size(self._font_size + 1)

    def _decrease_font_size(self) -> None:
        self._set_font_size(self._font_size - 1)

    def _set_font_size(self, size: int) -> None:
        size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, size))
        if size == self._font_size:
            return
        self._font_size = size
        self.input_text.config(font=("Arial", size))
        self.output_text.config(font=("Arial", size))

    def _save_log(self) -> None:
        self.logger.save(self._last_source, self._last_result)

    def _save_settings(self) -> None:
        AppSettings(
            dest_lang=self._dest_lang,
            ocr_enabled=self._ocr_enabled,
            overwrite_clipboard=self._overwrite_clipboard,
            font_size=self._font_size,
            window_width=self.root.winfo_width(),
            window_height=self.root.winfo_height(),
        ).save()
        self._settings_saved_var.set("Saved ✓")
        if self._settings_window is not None:
            self._settings_window.after(1500, lambda: self._settings_saved_var.set(""))

    def _update_title(self) -> None:
        self.root.title(f"Translate to {self._dest_lang}; Log: {self.logger.log_name}")

    def _update_status(self) -> None:
        ocr_state = "on" if self._ocr_enabled else "off"
        parts = [f"→ {self._dest_lang.upper()}", f"OCR: {ocr_state}"]
        if self._busy_event.is_set():
            parts.append("Translating...")
        self._status_var.set("   |   ".join(parts))

    # ---- lifecycle ------------------------------------------------------

    def run(self) -> None:
        self._watcher.start()
        self._worker.start()
        self.root.after(RESULT_POLL_MS, self._poll_results)
        self.root.after(EDIT_POLL_MS, self._poll_input_edits)
        self.root.mainloop()

    def _on_close(self) -> None:
        self._watcher.stop()
        self._request_queue.put(None)  # wake worker so it can exit
        self.root.destroy()
