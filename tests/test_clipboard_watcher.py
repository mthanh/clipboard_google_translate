import threading
import time
from unittest.mock import patch

from clipboard_google_translate.clipboard_watcher import ClipboardWatcher


def test_watcher_calls_on_change_only_when_clipboard_content_changes():
    values = iter(["a", "a", "b", "b"])
    seen = []
    ready = threading.Event()

    def on_change(text):
        seen.append(text)
        if len(seen) == 2:
            ready.set()

    with patch(
        "clipboard_google_translate.clipboard_watcher.pyperclip.paste",
        side_effect=lambda: next(values, "b"),
    ):
        watcher = ClipboardWatcher(on_change=on_change, poll_interval=0.01)
        watcher.start()
        try:
            assert ready.wait(timeout=2)
        finally:
            watcher.stop()
            watcher.join(timeout=2)

    assert seen == ["a", "b"]


def test_mark_seen_suppresses_the_next_matching_value():
    seen = []

    with patch(
        "clipboard_google_translate.clipboard_watcher.pyperclip.paste",
        return_value="x",
    ):
        watcher = ClipboardWatcher(on_change=seen.append, poll_interval=0.01)
        watcher.mark_seen("x")
        watcher.start()
        time.sleep(0.05)
        watcher.stop()
        watcher.join(timeout=2)

    assert seen == []
