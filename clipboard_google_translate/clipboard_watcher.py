"""Background clipboard polling.

Tkinter is not thread-safe: touching a widget from any thread other than
the one running mainloop() is a common source of the random freezes/crashes
the original implementation had. This watcher only talks to the OS
clipboard via pyperclip -- it never touches a Tk widget -- so it's safe to
run on its own thread. UI updates are handled elsewhere, on the Tk thread.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import pyperclip


class ClipboardWatcher(threading.Thread):
    def __init__(
        self,
        on_change: Callable[[str], None],
        poll_interval: float = 0.3,
    ) -> None:
        super().__init__(daemon=True, name="ClipboardWatcher")
        self._on_change = on_change
        self._poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._last_seen: Optional[str] = None

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                current = pyperclip.paste()
            except Exception:
                current = None

            if current is not None and current != self._last_seen:
                self._last_seen = current
                self._on_change(current)

            self._stop_event.wait(self._poll_interval)

    def stop(self) -> None:
        self._stop_event.set()

    def mark_seen(self, text: str) -> None:
        """Record `text` as already-seen so it won't re-trigger on_change.

        Call after writing to the clipboard programmatically (e.g. copying
        the translated result back) so the watcher doesn't mistake its own
        write for a fresh user copy.
        """
        self._last_seen = text
