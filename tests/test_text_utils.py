from clipboard_google_translate.text_utils import has_visible_text, remove_newlines


def test_remove_newlines_collapses_all_variants():
    assert remove_newlines("a\r\nb\n\rc\rd\ne") == "a b c d e"


def test_remove_newlines_leaves_text_without_newlines_unchanged():
    assert remove_newlines("hello world") == "hello world"


def test_has_visible_text_true_for_non_blank():
    assert has_visible_text("hello") is True


def test_has_visible_text_false_for_whitespace_only():
    assert has_visible_text("   \n\t  ") is False


def test_has_visible_text_false_for_empty_string():
    assert has_visible_text("") is False
