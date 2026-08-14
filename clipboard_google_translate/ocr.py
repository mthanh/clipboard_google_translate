"""OCR for images copied to the clipboard.

Uses Windows' built-in OCR engine (Windows.Media.Ocr) via the winrt
projection packages, so there's no extra binary to bundle/install (unlike
Tesseract). The catch: it only reads languages that have the "Optical
character recognition" feature installed under Windows Settings > Time &
language > Language & region -- the engine silently has nothing to work
with if that's missing.
"""

from __future__ import annotations

import asyncio
import io

from PIL import Image
from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream


class OcrError(Exception):
    """Raised when OCR can't be performed."""


class OcrService:
    def __init__(self) -> None:
        self._engine = OcrEngine.try_create_from_user_profile_languages()

    def recognize(self, image: Image.Image) -> str:
        if self._engine is None:
            raise OcrError(
                "No OCR language installed. Add one under Windows Settings > "
                "Time & language > Language & region, then enable "
                "'Optical character recognition' for it."
            )
        try:
            return asyncio.run(self._recognize_async(image))
        except Exception as exc:
            raise OcrError(str(exc)) from exc

    async def _recognize_async(self, image: Image.Image) -> str:
        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="PNG")

        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream.get_output_stream_at(0))
        writer.write_bytes(bytearray(buf.getvalue()))
        await writer.store_async()
        await writer.flush_async()
        stream.seek(0)

        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()

        result = await self._engine.recognize_async(bitmap)
        return result.text
