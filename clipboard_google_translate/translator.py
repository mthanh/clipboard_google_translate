"""Translation backend.

Wraps deep-translator's GoogleTranslator, which talks to Google's free
public translate endpoint (no API key, no billing). The old googletrans
3.1.0a0 dependency broke often ("NoneType object has no attribute group")
whenever Google tweaked that endpoint; deep-translator is actively
maintained and fails with a clear exception instead.
"""

from __future__ import annotations

from deep_translator import GoogleTranslator

from .text_utils import has_visible_text


class TranslationError(Exception):
    """Raised when a translation request fails."""


class TranslationService:
    def __init__(self) -> None:
        self._engines: dict[tuple[str, str], GoogleTranslator] = {}

    def _engine(self, src: str, dest: str) -> GoogleTranslator:
        key = (src, dest)
        engine = self._engines.get(key)
        if engine is None:
            engine = GoogleTranslator(source=src, target=dest)
            self._engines[key] = engine
        return engine

    def translate(self, text: str, dest: str, src: str = "auto") -> str:
        """Translate a single block of text. Empty/blank input returns "" ."""
        if not has_visible_text(text):
            return ""
        try:
            result = self._engine(src, dest).translate(text)
        except Exception as exc:  # deep-translator raises several exception types
            raise TranslationError(str(exc)) from exc
        return result or ""

    def translate_lines(self, text: str, dest: str, src: str = "auto") -> str:
        """Translate multi-line text, keeping blank lines and line order.

        Sends all non-blank lines to Google in a single batch call instead
        of one request per line, which is both faster and less likely to
        get rate-limited on long pasted text.
        """
        lines = text.splitlines()
        indices_to_translate = [i for i, line in enumerate(lines) if has_visible_text(line)]
        if not indices_to_translate:
            return "\n".join(lines)

        try:
            translated = self._engine(src, dest).translate_batch(
                [lines[i] for i in indices_to_translate]
            )
        except Exception as exc:
            raise TranslationError(str(exc)) from exc

        result_lines = list(lines)
        for i, translated_line in zip(indices_to_translate, translated):
            result_lines[i] = translated_line or ""
        return "\n".join(result_lines)
