from clipboard_google_translate.text_utils import (
    has_visible_text,
    reflow_sentences,
    remove_newlines,
    split_into_sentences,
)


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


def test_split_into_sentences_basic():
    assert split_into_sentences("Hello world. How are you? I am fine!") == [
        "Hello world.",
        "How are you?",
        "I am fine!",
    ]


def test_split_into_sentences_keeps_ellipsis_as_one_token():
    assert split_into_sentences("Wait... really? I'm fine!") == [
        "Wait...",
        "really?",
        "I'm fine!",
    ]


def test_split_into_sentences_ignores_existing_line_breaks():
    assert split_into_sentences("Hello\nworld. How\nare you?") == [
        "Hello world.",
        "How are you?",
    ]


def test_split_into_sentences_keeps_trailing_fragment_without_punctuation():
    assert split_into_sentences("First sentence. trailing fragment") == [
        "First sentence.",
        "trailing fragment",
    ]


def test_split_into_sentences_handles_cjk_punctuation():
    assert split_into_sentences("こんにちは。元気ですか?") == ["こんにちは。", "元気ですか?"]


def test_split_into_sentences_empty_input():
    assert split_into_sentences("   ") == []


def test_reflow_sentences_joins_with_newlines():
    assert reflow_sentences("Hello world. How are\nyou?") == "Hello world.\nHow are you?"
