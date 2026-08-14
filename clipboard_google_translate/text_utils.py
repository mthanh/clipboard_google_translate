"""Small text helpers used across the app."""


def remove_newlines(text: str) -> str:
    """Collapse all line-break variants into a single space.

    Useful for text copied from PDFs, where every wrapped line ends in a
    hard newline that Google Translate would otherwise treat as a sentence
    break.
    """
    for newline in ("\r\n", "\n\r", "\r", "\n"):
        text = text.replace(newline, " ")
    return text


def has_visible_text(text: str) -> bool:
    """True if text contains at least one non-whitespace character."""
    return bool(text.strip())
