"""Engine adapters for the OCR bake-off.

Each adapter exposes the same shape: construct() records cold init time,
run(image_bgr) returns a BenchResult with per-line (bbox, text, confidence)
plus whatever detection/recognition timing split the underlying library
actually exposes — None where it doesn't, rather than a fabricated number.
"""

import time
from dataclasses import dataclass, field

import numpy as np
from PIL import Image


@dataclass
class BenchLine:
    bbox: tuple[float, float, float, float]  # x, y, w, h
    text: str
    confidence: float


@dataclass
class BenchResult:
    lines: list[BenchLine]
    total_s: float
    detect_s: float | None = None
    recognize_s: float | None = None


def _quad_to_bbox(quad) -> tuple[float, float, float, float]:
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return (float(x0), float(y0), float(x1 - x0), float(y1 - y0))


class BenchEngine:
    name: str

    def construct(self) -> float:
        t0 = time.perf_counter()
        self._construct()
        return time.perf_counter() - t0

    def _construct(self) -> None:
        raise NotImplementedError

    def run(self, image_bgr: np.ndarray) -> BenchResult:
        raise NotImplementedError


class PaddleEngine(BenchEngine):
    """Mirrors services/pipeline/ocr_engine.py exactly — same model names,
    same disabled preprocessing stages, same enable_mkldnn=False workaround.
    This IS the production configuration, not a re-implementation of it.
    """

    name = "paddle_ppocrv5_mobile"

    def _construct(self) -> None:
        from paddleocr import PaddleOCR

        self._ocr = PaddleOCR(
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="PP-OCRv5_mobile_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        )

    def run(self, image_bgr: np.ndarray) -> BenchResult:
        t0 = time.perf_counter()
        results = self._ocr.predict(image_bgr)
        total_s = time.perf_counter() - t0

        lines: list[BenchLine] = []
        for res in results:
            texts = res["rec_texts"]
            scores = res["rec_scores"]
            polys = res["rec_polys"]
            for text, score, poly in zip(texts, scores, polys):
                lines.append(BenchLine(bbox=_quad_to_bbox(poly), text=text, confidence=float(score)))
        # PaddleOCR's predict() is one opaque end-to-end pipeline call — no
        # public hook splits detection from recognition wall-time (production's
        # own stages/detect.py only measures this same combined ocr_run_s).
        return BenchResult(lines=lines, total_s=total_s, detect_s=None, recognize_s=None)


class RapidEngine(BenchEngine):
    """RapidOCR running the exact PP-OCRv5 mobile 'ch' det/rec ONNX export
    that ships for both engine_types (identical SHA256 in RapidOCR's own
    default_models.yaml) — isolates inference runtime (ONNX Runtime vs
    OpenVINO), not model choice.
    """

    def __init__(self, engine_type: str) -> None:
        self._engine_type = engine_type
        self.name = f"rapidocr_ppocrv5_mobile_{engine_type}"

    def _construct(self) -> None:
        from rapidocr import RapidOCR
        from rapidocr.utils.typings import EngineType, LangDet, LangRec, ModelType, OCRVersion

        engine = EngineType.ONNXRUNTIME if self._engine_type == "onnxruntime" else EngineType.OPENVINO
        self._ocr = RapidOCR(
            params={
                "Det.engine_type": engine,
                "Det.ocr_version": OCRVersion.PPOCRV5,
                "Det.model_type": ModelType.MOBILE,
                "Det.lang_type": LangDet.CH,
                "Rec.engine_type": engine,
                "Rec.ocr_version": OCRVersion.PPOCRV5,
                "Rec.model_type": ModelType.MOBILE,
                "Rec.lang_type": LangRec.CH,
                "Global.use_cls": False,
            }
        )

    def run(self, image_bgr: np.ndarray) -> BenchResult:
        image_rgb = np.ascontiguousarray(image_bgr[:, :, ::-1])
        t0 = time.perf_counter()
        res = self._ocr(image_rgb)
        total_s = time.perf_counter() - t0

        lines: list[BenchLine] = []
        if res.boxes is not None:
            for box, text, score in zip(res.boxes, res.txts, res.scores):
                lines.append(BenchLine(bbox=_quad_to_bbox(box), text=text, confidence=float(score)))

        # elapse_list is [det_s, cls_s, rec_s]; cls is disabled (None) here.
        detect_s = None
        recognize_s = None
        if res.elapse_list is not None and len(res.elapse_list) == 3:
            detect_s = res.elapse_list[0]
            recognize_s = res.elapse_list[2]
        return BenchResult(lines=lines, total_s=total_s, detect_s=detect_s, recognize_s=recognize_s)


class TesseractEngine(BenchEngine):
    """Tesseract 5 via pytesseract. No detection/recognition split is exposed
    (image_to_data is one call covering layout analysis + recognition), and
    Tesseract's own layout analysis groups words into (block, par, line) —
    that grouping is used here as-is to build per-line regions, rather than
    inventing a line segmentation Tesseract doesn't naturally produce.
    """

    name = "tesseract5"

    def _construct(self) -> None:
        import pytesseract

        self._pytesseract = pytesseract
        # One throwaway call to pay any first-call process/page-cache cost
        # under a controlled, timed construct() rather than silently
        # inside the first real measurement.
        blank = Image.new("RGB", (64, 64), "white")
        pytesseract.image_to_data(blank, output_type=pytesseract.Output.DICT)

    def run(self, image_bgr: np.ndarray) -> BenchResult:
        image = Image.fromarray(image_bgr[:, :, ::-1])
        t0 = time.perf_counter()
        data = self._pytesseract.image_to_data(image, output_type=self._pytesseract.Output.DICT)
        total_s = time.perf_counter() - t0

        groups: dict[tuple[int, int, int], list[int]] = {}
        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])
            if not text or conf < 0:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            groups.setdefault(key, []).append(i)

        lines: list[BenchLine] = []
        for key, idxs in sorted(groups.items()):
            idxs = sorted(idxs, key=lambda i: data["word_num"][i])
            words = [data["text"][i].strip() for i in idxs]
            lefts = [data["left"][i] for i in idxs]
            tops = [data["top"][i] for i in idxs]
            rights = [data["left"][i] + data["width"][i] for i in idxs]
            bottoms = [data["top"][i] + data["height"][i] for i in idxs]
            confs = [int(data["conf"][i]) for i in idxs]
            x0, y0, x1, y1 = min(lefts), min(tops), max(rights), max(bottoms)
            lines.append(
                BenchLine(
                    bbox=(float(x0), float(y0), float(x1 - x0), float(y1 - y0)),
                    text=" ".join(words),
                    confidence=(sum(confs) / len(confs)) / 100.0,
                )
            )
        return BenchResult(lines=lines, total_s=total_s, detect_s=None, recognize_s=None)


def make_engines() -> list[BenchEngine]:
    return [
        PaddleEngine(),
        RapidEngine("onnxruntime"),
        RapidEngine("openvino"),
        TesseractEngine(),
    ]
