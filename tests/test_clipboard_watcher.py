import threading
import time
from unittest.mock import patch

from PIL import Image

from clipboard_google_translate.clipboard_watcher import ClipboardWatcher


def _watcher(on_text_change=None, on_image_change=None, poll_interval=0.01):
    return ClipboardWatcher(
        on_text_change=on_text_change or (lambda text: None),
        on_image_change=on_image_change or (lambda image: None),
        poll_interval=poll_interval,
    )


def test_watcher_calls_on_text_change_only_when_content_changes():
    values = iter(["a", "a", "b", "b"])
    seen = []
    ready = threading.Event()

    def on_text_change(text):
        seen.append(text)
        if len(seen) == 2:
            ready.set()

    with (
        patch(
            "clipboard_google_translate.clipboard_watcher.ImageGrab.grabclipboard",
            return_value=None,
        ),
        patch(
            "clipboard_google_translate.clipboard_watcher.pyperclip.paste",
            side_effect=lambda: next(values, "b"),
        ),
    ):
        watcher = _watcher(on_text_change=on_text_change)
        watcher.start()
        try:
            assert ready.wait(timeout=2)
        finally:
            watcher.stop()
            watcher.join(timeout=2)

    assert seen == ["a", "b"]


def test_mark_seen_suppresses_the_next_matching_text():
    seen = []

    with (
        patch(
            "clipboard_google_translate.clipboard_watcher.ImageGrab.grabclipboard",
            return_value=None,
        ),
        patch(
            "clipboard_google_translate.clipboard_watcher.pyperclip.paste",
            return_value="x",
        ),
    ):
        watcher = _watcher(on_text_change=seen.append)
        watcher.mark_seen("x")
        watcher.start()
        time.sleep(0.05)
        watcher.stop()
        watcher.join(timeout=2)

    assert seen == []


def test_watcher_calls_on_image_change_when_clipboard_has_an_image():
    image = Image.new("RGB", (2, 2), "white")
    seen = []
    ready = threading.Event()

    def on_image_change(img):
        seen.append(img)
        ready.set()

    with patch(
        "clipboard_google_translate.clipboard_watcher.ImageGrab.grabclipboard",
        return_value=image,
    ):
        watcher = _watcher(on_image_change=on_image_change)
        watcher.start()
        try:
            assert ready.wait(timeout=2)
        finally:
            watcher.stop()
            watcher.join(timeout=2)

    assert seen == [image]


def test_watcher_does_not_retrigger_on_image_change_for_the_same_image():
    image = Image.new("RGB", (2, 2), "white")
    seen = []

    with patch(
        "clipboard_google_translate.clipboard_watcher.ImageGrab.grabclipboard",
        return_value=image,
    ):
        watcher = _watcher(on_image_change=seen.append)
        watcher.start()
        time.sleep(0.05)
        watcher.stop()
        watcher.join(timeout=2)

    assert len(seen) == 1
