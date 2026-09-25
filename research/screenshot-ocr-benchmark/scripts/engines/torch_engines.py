"""easyocr and doctr adapters (PyTorch, CPU).

easyocr: Reader(['en'], gpu=False), readtext(detail=1, paragraph=False). The
image is passed as a BGR numpy array, which is EasyOCR's documented numpy
convention ("an OpenCV image object").

doctr: ocr_predictor(pretrained=True) with library defaults; lines are taken
from export() blocks -> lines, text = words joined by single spaces.
"""

import os
import time

from base import Engine, Line, Result, quad_to_bbox, sha256_tree


def bake() -> None:
    import numpy as np

    import easyocr
    from doctr.models import ocr_predictor

    blank = np.full((64, 256, 3), 255, dtype=np.uint8)
    easyocr.Reader(["en"], gpu=False).readtext(blank)
    ocr_predictor(pretrained=True)([blank])
    print("baked easyocr + doctr")


class EasyOcrEngine(Engine):
    engine_id = "easyocr"

    def __init__(self) -> None:
        self.config = {"lang_list": ["en"], "gpu": False, "readtext": {"detail": 1, "paragraph": False},
                       "input": "BGR uint8 ndarray"}

    def _construct(self) -> None:
        import easyocr

        self._reader = easyocr.Reader(["en"], gpu=False)

    def run(self, image_rgb) -> Result:
        bgr = image_rgb[:, :, ::-1].copy()
        t0 = time.perf_counter()
        out = self._reader.readtext(bgr, detail=1, paragraph=False)
        total_s = time.perf_counter() - t0
        lines = [Line(bbox=quad_to_bbox(quad), text=str(text), confidence=float(conf)) for quad, text, conf in out]
        return Result(lines=lines, total_s=total_s)

    def info(self) -> dict:
        import easyocr
        import torch

        return {
            "engine_id": self.engine_id,
            "engine_version": f"easyocr {easyocr.__version__} / torch {torch.__version__}",
            "config": self.config,
            "weights_sha256": sha256_tree(os.path.expanduser("~/.EasyOCR/model")),
            "torch_num_threads": torch.get_num_threads(),
        }


class DoctrEngine(Engine):
    engine_id = "doctr"

    def __init__(self) -> None:
        self.config = {"ocr_predictor": {"pretrained": True}, "input": "RGB uint8 ndarray"}

    def _construct(self) -> None:
        from doctr.models import ocr_predictor

        self._model = ocr_predictor(pretrained=True)

    def run(self, image_rgb) -> Result:
        h, w = image_rgb.shape[:2]
        t0 = time.perf_counter()
        doc = self._model([image_rgb])
        total_s = time.perf_counter() - t0
        lines: list[Line] = []
        for block in doc.export()["pages"][0]["blocks"]:
            for line in block["lines"]:
                (x0, y0), (x1, y1) = line["geometry"]
                words = line["words"]
                text = " ".join(word["value"] for word in words)
                conf = min((float(word["confidence"]) for word in words), default=None)
                lines.append(Line(bbox=(x0 * w, y0 * h, (x1 - x0) * w, (y1 - y0) * h), text=text, confidence=conf))
        return Result(lines=lines, total_s=total_s)

    def info(self) -> dict:
        import doctr
        import torch

        det = type(self._model.det_predictor.model).__name__
        reco = type(self._model.reco_predictor.model).__name__
        return {
            "engine_id": self.engine_id,
            "engine_version": f"python-doctr {doctr.__version__} / torch {torch.__version__}",
            "config": {**self.config, "det_model": det, "reco_model": reco},
            "weights_sha256": sha256_tree(os.path.expanduser("~/.cache/doctr/models")),
            "torch_num_threads": torch.get_num_threads(),
        }
