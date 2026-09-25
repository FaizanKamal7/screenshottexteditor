"""windows_ocr adapter: Windows.Media.Ocr (en-US) via the pywinrt bindings.

Runs natively on the Windows host. The decoded RGB pixels are converted to a
BGRA8 SoftwareBitmap before timing starts, so the timed region is only
RecognizeAsync. Windows OCR reports no per-line confidence, so confidence is
None rather than an invented value. Line boxes are the union of each line's
word rectangles, as the API reports them.
"""

import asyncio
import platform
import time
from importlib import metadata

import numpy as np

from base import Engine, Line, Result


class WindowsOcrEngine(Engine):
    engine_id = "windows_ocr"

    def __init__(self) -> None:
        self.config = {"language": "en-US", "pixel_format": "BGRA8", "alpha_mode": "PREMULTIPLIED"}

    def _construct(self) -> None:
        from winrt.windows.globalization import Language
        from winrt.windows.media.ocr import OcrEngine

        self._engine = OcrEngine.try_create_from_language(Language("en-US"))
        if self._engine is None:
            raise RuntimeError("Windows OCR en-US recognizer is not installed")

    def _bitmap(self, image_rgb):
        from winrt.windows.graphics.imaging import BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap
        from winrt.windows.storage.streams import Buffer

        h, w = image_rgb.shape[:2]
        bgra = np.empty((h, w, 4), dtype=np.uint8)
        bgra[:, :, 0] = image_rgb[:, :, 2]
        bgra[:, :, 1] = image_rgb[:, :, 1]
        bgra[:, :, 2] = image_rgb[:, :, 0]
        bgra[:, :, 3] = 255
        raw = bgra.tobytes()
        buf = Buffer(len(raw))
        buf.length = len(raw)
        memoryview(buf)[:] = raw
        bitmap = SoftwareBitmap(BitmapPixelFormat.BGRA8, w, h, BitmapAlphaMode.PREMULTIPLIED)
        bitmap.copy_from_buffer(buf)
        return bitmap

    def run(self, image_rgb) -> Result:
        bitmap = self._bitmap(image_rgb)
        t0 = time.perf_counter()
        ocr_result = asyncio.run(self._recognize(bitmap))
        total_s = time.perf_counter() - t0
        lines: list[Line] = []
        for line in ocr_result.lines:
            rects = [word.bounding_rect for word in line.words]
            if not rects:
                continue
            x0 = min(r.x for r in rects)
            y0 = min(r.y for r in rects)
            x1 = max(r.x + r.width for r in rects)
            y1 = max(r.y + r.height for r in rects)
            lines.append(Line(bbox=(float(x0), float(y0), float(x1 - x0), float(y1 - y0)), text=line.text,
                              confidence=None))
        return Result(lines=lines, total_s=total_s)

    async def _recognize(self, bitmap):
        return await self._engine.recognize_async(bitmap)

    def info(self) -> dict:
        from winrt.windows.media.ocr import OcrEngine

        packages = {}
        for dist in ("winrt-runtime", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging"):
            try:
                packages[dist] = metadata.version(dist)
            except metadata.PackageNotFoundError:
                packages[dist] = None
        return {
            "engine_id": self.engine_id,
            "engine_version": f"Windows.Media.Ocr on Windows {platform.version()}",
            "config": {**self.config, "recognizer_language": self._engine.recognizer_language.language_tag},
            "max_image_dimension": OcrEngine.max_image_dimension,
            "python_packages": packages,
            "weights_sha256": None,
        }
