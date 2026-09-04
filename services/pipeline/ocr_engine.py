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

        # 3.x replaces 2.x's use_angle_cls with use_textline_orientation, and
        # adds two new pipeline stages (doc orientation / unwarping) that 2.x
        # never had — both disabled here since screenshots are neither
        # rotated nor scanned, keeping behavior close to the old lightweight
        # default rather than paying for new preprocessing stages we don't need.
        self._ocr = PaddleOCR(
            # PP-OCRv6_medium (the 3.7 default) is tuned for accuracy over
            # speed; PP-OCRv5_mobile is smaller and meaningfully faster to
            # both load and run — chosen after comparing round-trip
            # accuracy against PP-OCRv6_medium (see docs/pipeline-tuning.md).
            # lang isn't passed here: paddleocr only uses it to pick a
            # default model set, and ignores it (with a warning) once
            # explicit model names are given below.
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="PP-OCRv5_mobile_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            # paddlepaddle 3.3.1's oneDNN CPU kernel path throws
            # `NotImplementedError: ConvertPirAttribute2RuntimeAttribute not
            # support [pir::ArrayAttribute<pir::DoubleAttribute>]` on
            # PP-OCRv6's detection model — a paddlepaddle bug, not anything
            # about this image or model config. Disabling oneDNN routes
            # inference through the plain CPU kernel path instead.
            enable_mkldnn=False,
        )

    def run(self, image_bgr: np.ndarray) -> list[RawLine]:
        # .ocr()/.predict() are equivalent in 3.x for this pipeline; predict()
        # is the non-deprecated entry point. Each result is dict-like, keyed
        # by rec_texts/rec_scores/rec_polys (a quad per line, same shape 2.x's
        # raw quad was) rather than 2.x's list-of-(quad, (text, confidence)).
        results = self._ocr.predict(image_bgr)
        lines: list[RawLine] = []
        for res in results:
            texts = res["rec_texts"]
            scores = res["rec_scores"]
            polys = res["rec_polys"]
            for text, score, poly in zip(texts, scores, polys):
                lines.append(
                    RawLine(
                        quad=[(float(x), float(y)) for x, y in poly],
                        text=text,
                        confidence=float(score),
                    )
                )
        return lines


@lru_cache(maxsize=1)
def get_ocr_engine() -> OcrEngine:
    return OcrEngine()
