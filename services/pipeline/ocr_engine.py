from dataclasses import dataclass
from functools import lru_cache

import numpy as np


@dataclass
class RawLine:
    quad: list[tuple[float, float]]
    text: str
    confidence: float


class OcrEngine:
    """Thin wrapper around PaddleOCR.

    Isolated here so a PaddleOCR version bump or engine swap is a
    one-file change rather than a rewrite of stages/detect.py.
    """

    def __init__(self) -> None:
        from paddleocr import PaddleOCR

        self._ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)

    def run(self, image_bgr: np.ndarray) -> list[RawLine]:
        raw_result = self._ocr.ocr(image_bgr, cls=False)
        lines: list[RawLine] = []
        for page in raw_result or []:
            for quad, (text, confidence) in page or []:
                lines.append(
                    RawLine(
                        quad=[(float(x), float(y)) for x, y in quad],
                        text=text,
                        confidence=float(confidence),
                    )
                )
        return lines


@lru_cache(maxsize=1)
def get_ocr_engine() -> OcrEngine:
    return OcrEngine()
