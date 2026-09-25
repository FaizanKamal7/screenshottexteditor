"""paddle_v5_mobile / paddle_v5_server adapters (PaddleOCR 3.x, PP-OCRv5).

Adapted from services/pipeline/bench/engines.py's PaddleEngine. Pilot
configuration (PREREGISTRATION D1 is still open; this is the provisional
choice, recorded in engines.lock.json):
- recognition model: the multilingual PP-OCRv5 rec model (same family the
  production pipeline and the existing bench use);
- doc orientation / unwarping / text-line orientation disabled: screenshots are
  never rotated or warped (METHODOLOGY §7);
- enable_mkldnn=False: the production value, pending D1.
"""

import os
import time

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from base import Engine, Line, Result, quad_to_bbox, sha256_tree

MODELS = {
    "paddle_v5_mobile": ("PP-OCRv5_mobile_det", "PP-OCRv5_mobile_rec"),
    "paddle_v5_server": ("PP-OCRv5_server_det", "PP-OCRv5_server_rec"),
}

FLAGS = {
    "use_doc_orientation_classify": False,
    "use_doc_unwarping": False,
    "use_textline_orientation": False,
    "enable_mkldnn": False,
}


def _make(engine_id: str):
    from paddleocr import PaddleOCR

    det, rec = MODELS[engine_id]
    return PaddleOCR(text_detection_model_name=det, text_recognition_model_name=rec, **FLAGS)


def bake() -> None:
    """Download every model at image build time (containers run offline)."""
    import numpy as np

    for engine_id in MODELS:
        ocr = _make(engine_id)
        ocr.predict(np.full((64, 256, 3), 255, dtype=np.uint8))
        print(f"baked {engine_id}")


class PaddleEngine(Engine):
    def __init__(self, engine_id: str) -> None:
        self.engine_id = engine_id
        det, rec = MODELS[engine_id]
        self.config = {"text_detection_model_name": det, "text_recognition_model_name": rec, **FLAGS}

    def _construct(self) -> None:
        self._ocr = _make(self.engine_id)

    def run(self, image_rgb) -> Result:
        bgr = image_rgb[:, :, ::-1].copy()
        t0 = time.perf_counter()
        results = self._ocr.predict(bgr)
        total_s = time.perf_counter() - t0
        lines: list[Line] = []
        for res in results:
            for text, score, poly in zip(res["rec_texts"], res["rec_scores"], res["rec_polys"]):
                lines.append(Line(bbox=quad_to_bbox(poly), text=str(text), confidence=float(score)))
        # predict() is one opaque call; no public detection/recognition split.
        return Result(lines=lines, total_s=total_s)

    def info(self) -> dict:
        import paddle
        import paddleocr

        models_root = os.path.expanduser("~/.paddlex/official_models")
        weights = {name: sha256_tree(os.path.join(models_root, name)) for name in MODELS[self.engine_id]}
        return {
            "engine_id": self.engine_id,
            "engine_version": f"paddleocr {paddleocr.__version__} / paddlepaddle {paddle.__version__}",
            "config": self.config,
            "weights_sha256": weights,
        }
