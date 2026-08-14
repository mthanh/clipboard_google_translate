"""Small text helpers used across the app."""

import re

# One or more terminal-punctuation characters (covers CJK full-width
# variants too), captured as a group so re.split keeps it attached to the
# sentence it ends -- "Wait..." stays one token instead of splitting on
# every dot.
_SENTENCE_END_RE = re.compile(r"([.!?。!?]+)\s*")


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


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences on terminal punctuation (.!?。!?).

    Existing line breaks are ignored (treated as ordinary whitespace)
    first, so a sentence that was hard-wrapped across lines is rejoined
    before being split back out by punctuation.
    """
    collapsed = " ".join(remove_newlines(text).split())
    if not collapsed:
        return []

    parts = _SENTENCE_END_RE.split(collapsed)
    sentences = []
    for i in range(0, len(parts) - 1, 2):
        sentence = (parts[i] + parts[i + 1]).strip()
        if sentence:
            sentences.append(sentence)
    trailing = parts[-1].strip() if len(parts) % 2 == 1 else ""
    if trailing:
        sentences.append(trailing)
    return sentences


def reflow_sentences(text: str) -> str:
    """Remove existing line breaks and put each sentence on its own line."""
    return "\n".join(split_into_sentences(text))
