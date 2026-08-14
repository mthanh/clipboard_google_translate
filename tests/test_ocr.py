from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from clipboard_google_translate.ocr import OcrError, OcrService


def make_image():
    return Image.new("RGB", (2, 2), "white")


@patch("clipboard_google_translate.ocr.OcrEngine")
def test_recognize_raises_when_no_language_pack_installed(mock_engine_cls):
    mock_engine_cls.try_create_from_user_profile_languages.return_value = None
    service = OcrService()

    with pytest.raises(OcrError):
        service.recognize(make_image())


@patch("clipboard_google_translate.ocr.OcrEngine")
def test_recognize_returns_text_from_the_engine(mock_engine_cls):
    mock_engine_cls.try_create_from_user_profile_languages.return_value = MagicMock()
    service = OcrService()
    service._recognize_async = AsyncMock(return_value="hello world")

    assert service.recognize(make_image()) == "hello world"


@patch("clipboard_google_translate.ocr.OcrEngine")
def test_recognize_wraps_backend_errors(mock_engine_cls):
    mock_engine_cls.try_create_from_user_profile_languages.return_value = MagicMock()
    service = OcrService()
    service._recognize_async = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(OcrError):
        service.recognize(make_image())
