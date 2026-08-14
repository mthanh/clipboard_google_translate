"""Background clipboard polling.

Tkinter is not thread-safe: touching a widget from any thread other than
the one running mainloop() is a common source of the random freezes/crashes
the original implementation had. This watcher only talks to the OS
clipboard via pyperclip/Pillow -- it never touches a Tk widget -- so it's
safe to run on its own thread. UI updates are handled elsewhere, on the Tk
thread.
"""

from __future__ import annotations

import hashlib
import threading
from typing import Callable, Optional

import pyperclip
from PIL import Image, ImageGrab


class ClipboardWatcher(threading.Thread):
    def __init__(
        self,
        on_text_change: Callable[[str], None],
        on_image_change: Callable[[Image.Image], None],
        poll_interval: float = 0.3,
    ) -> None:
        super().__init__(daemon=True, name="ClipboardWatcher")
        self._on_text_change = on_text_change
        self._on_image_change = on_image_change
        self._poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._last_text: Optional[str] = None
        self._last_image_hash: Optional[bytes] = None

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                content = ImageGrab.grabclipboard()
            except Exception:
                content = None

            if isinstance(content, Image.Image):
                self._handle_image(content)
            else:
                self._handle_text()

            self._stop_event.wait(self._poll_interval)

    def _handle_image(self, image: Image.Image) -> None:
        image_hash = hashlib.md5(image.tobytes()).digest()
        if image_hash != self._last_image_hash:
            self._last_image_hash = image_hash
            self._on_image_change(image)

    def _handle_text(self) -> None:
        try:
            current = pyperclip.paste()
        except Exception:
            current = None

        if current is not None and current != self._last_text:
            self._last_text = current
            self._on_text_change(current)

    def stop(self) -> None:
        self._stop_event.set()

    def mark_seen(self, text: str) -> None:
        """Record `text` as already-seen so it won't re-trigger on_text_change.

        Call after writing to the clipboard programmatically (e.g. copying
        the translated result back) so the watcher doesn't mistake its own
        write for a fresh user copy.
        """
        self._last_text = text
