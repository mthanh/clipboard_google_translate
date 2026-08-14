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
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import WORD, Button, Checkbutton, Text
from typing import NamedTuple, Optional

import pyperclip

from .clipboard_watcher import ClipboardWatcher
from .logger import TranslationLogger
from .text_utils import has_visible_text, remove_newlines
from .translator import TranslationError, TranslationService

RESULT_POLL_MS = 50
EDIT_POLL_MS = 300
LANGUAGES = (("VI", "vi"), ("JA", "ja"), ("EN", "en"))
SELECTED_BUTTON_BG = "#cfe8ff"


class TranslationRequest(NamedTuple):
    source_text: str


@dataclass
class TranslationResult:
    source_text: str
    translated_text: Optional[str]
    error: Optional[str] = None


class TranslatorApp:
    def __init__(self) -> None:
        self.root = tk.Tk()

        self.translator = TranslationService()
        self.logger = TranslationLogger()

        self._dest_lang = "vi"
        self._last_source = ""
        self._last_result = ""
        self._last_input_seen = ""

        # Plain bool, not tk.BooleanVar: the worker thread reads/writes this
        # flag, and Tk variables -- like widgets -- aren't thread-safe.
        # `_strip_pdf_newlines_var` below is the checkbox's own display
        # state; `_poll_results` keeps it mirroring this flag on the main
        # thread.
        self._strip_pdf_newlines = True
        self._strip_pdf_newlines_var = tk.BooleanVar(value=True)

        self._request_queue: "queue.Queue[Optional[TranslationRequest]]" = queue.Queue()
        self._result_queue: "queue.Queue[TranslationResult]" = queue.Queue()

        self._build_widgets()
        self._update_title()

        self._watcher = ClipboardWatcher(on_change=self._on_clipboard_change)
        self._worker = threading.Thread(
            target=self._translation_worker_loop, name="TranslationWorker", daemon=True
        )

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- UI construction -------------------------------------------------

    def _build_widgets(self) -> None:
        root = self.root

        self.input_text = Text(width=35, height=15, wrap=WORD, font=("Arial", 11))
        self.input_text.grid(row=1, column=0, pady=0, padx=0, columnspan=100, sticky=tk.W)

        self.output_text = Text(width=35, height=15, wrap=WORD, font=("Arial", 11))
        self.output_text.grid(row=1, column=101, columnspan=100, pady=0, padx=0, sticky=tk.W)

        self._lang_buttons: dict[str, Button] = {}
        self._default_button_bg: Optional[str] = None
        for col, (label, code) in enumerate(LANGUAGES):
            btn = Button(root, text=label, command=lambda c=code: self._set_dest_lang(c))
            btn.config(font=("NSimSun", 11))
            btn.grid(row=0, column=col, sticky=tk.W)
            self._lang_buttons[code] = btn
            if self._default_button_bg is None:
                self._default_button_bg = btn.cget("bg")
        self._highlight_selected_lang()

        Button(root, text="Save_Log", command=self._save_log, font=("NSimSun", 11)).grid(
            row=0, column=3, sticky=tk.W
        )
        Button(root, text="Open_Log", command=self.logger.open_folder, font=("NSimSun", 11)).grid(
            row=0, column=4, sticky=tk.W
        )

        Button(root, text="Copy_Result", command=self._copy_result_to_clipboard, font=("NSimSun", 11)).grid(
            row=0, column=101, sticky=tk.W
        )
        Button(root, text="CLEAR", command=self._clear_input, font=("NSimSun", 11)).grid(
            row=0, column=102, sticky=tk.W
        )
        Checkbutton(
            root,
            text="REMOVE_ENTER",
            variable=self._strip_pdf_newlines_var,
            command=self._on_toggle_strip_newlines,
            font=("NSimSun", 11),
        ).grid(row=0, column=103, sticky=tk.W)

    # ---- clipboard / edit -> translation request --------------------------

    def _on_clipboard_change(self, text: str) -> None:
        """Runs on the watcher thread. Must not touch Tk widgets."""
        if has_visible_text(text) and text != self._last_result:
            self._request_queue.put(TranslationRequest(source_text=text))

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

            source_text = request.source_text
            if self._strip_pdf_newlines:
                source_text = remove_newlines(source_text)
                self._strip_pdf_newlines = False  # one-shot: applies to the next paste only
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

        pyperclip.copy(self._last_result)
        self._watcher.mark_seen(self._last_result)

        self.root.call("wm", "attributes", ".", "-topmost", "1")
        self.root.after_idle(self.root.call, "wm", "attributes", ".", "-topmost", False)

    @staticmethod
    def _set_text(widget: Text, text: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", text)

    # ---- button actions -----------------------------------------------------

    def _on_toggle_strip_newlines(self) -> None:
        self._strip_pdf_newlines = self._strip_pdf_newlines_var.get()

    def _set_dest_lang(self, lang_code: str) -> None:
        self._dest_lang = lang_code
        self._highlight_selected_lang()
        self._update_title()
        current = self.input_text.get("1.0", "end-1c")
        if has_visible_text(current):
            self._request_queue.put(TranslationRequest(source_text=current))

    def _highlight_selected_lang(self) -> None:
        for code, btn in self._lang_buttons.items():
            if code == self._dest_lang:
                btn.config(relief=tk.SUNKEN, bg=SELECTED_BUTTON_BG)
            else:
                btn.config(relief=tk.RAISED, bg=self._default_button_bg)

    def _copy_result_to_clipboard(self) -> None:
        pyperclip.copy(self._last_result)
        self._watcher.mark_seen(self._last_result)

    def _clear_input(self) -> None:
        self.input_text.delete("1.0", "end")
        self._last_input_seen = ""

    def _save_log(self) -> None:
        self.logger.save(self._last_source, self._last_result)

    def _update_title(self) -> None:
        self.root.title(f"Translate to {self._dest_lang}; Log: {self.logger.log_name}")

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
