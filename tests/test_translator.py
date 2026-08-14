from unittest.mock import MagicMock, patch

import pytest

from clipboard_google_translate.translator import TranslationError, TranslationService


def make_engine(translate_return=None, translate_batch_return=None, raise_exc=None):
    engine = MagicMock()
    if raise_exc is not None:
        engine.translate.side_effect = raise_exc
        engine.translate_batch.side_effect = raise_exc
    else:
        engine.translate.return_value = translate_return
        engine.translate_batch.return_value = translate_batch_return
    return engine


@patch("clipboard_google_translate.translator.GoogleTranslator")
def test_translate_returns_engine_result(mock_cls):
    mock_cls.return_value = make_engine(translate_return="xin chao")
    service = TranslationService()

    assert service.translate("hello", dest="vi") == "xin chao"
    mock_cls.assert_called_once_with(source="auto", target="vi")


@patch("clipboard_google_translate.translator.GoogleTranslator")
def test_translate_blank_text_skips_network_call(mock_cls):
    service = TranslationService()

    assert service.translate("   ", dest="vi") == ""
    mock_cls.assert_not_called()


@patch("clipboard_google_translate.translator.GoogleTranslator")
def test_translate_wraps_backend_errors(mock_cls):
    mock_cls.return_value = make_engine(raise_exc=RuntimeError("boom"))
    service = TranslationService()

    with pytest.raises(TranslationError):
        service.translate("hello", dest="vi")


@patch("clipboard_google_translate.translator.GoogleTranslator")
def test_translate_lines_preserves_blank_lines_and_order(mock_cls):
    mock_cls.return_value = make_engine(translate_batch_return=["one", "two"])
    service = TranslationService()

    result = service.translate_lines("line1\n\nline2", dest="vi")

    assert result == "one\n\ntwo"


@patch("clipboard_google_translate.translator.GoogleTranslator")
def test_translate_lines_only_batches_non_blank_lines(mock_cls):
    engine = make_engine(translate_batch_return=["dich1", "dich2"])
    mock_cls.return_value = engine
    service = TranslationService()

    service.translate_lines("a\n\nb\n   ", dest="vi")

    engine.translate_batch.assert_called_once_with(["a", "b"])


@patch("clipboard_google_translate.translator.GoogleTranslator")
def test_translate_lines_all_blank_skips_network(mock_cls):
    service = TranslationService()

    result = service.translate_lines("   \n\t", dest="vi")

    assert result == "   \n\t"
    mock_cls.assert_not_called()


@patch("clipboard_google_translate.translator.GoogleTranslator")
def test_engine_reused_for_same_language_pair(mock_cls):
    mock_cls.return_value = make_engine(translate_return="x")
    service = TranslationService()

    service.translate("a", dest="vi")
    service.translate("b", dest="vi")

    assert mock_cls.call_count == 1
