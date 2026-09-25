"""tesseract5 adapter. Line grouping copied from services/pipeline/bench/engines.py:
Tesseract's own (block, paragraph, line) layout grouping is used as-is rather
than inventing a segmentation it doesn't produce. Config made explicit:
--oem 1 --psm 3, lang eng, tessdata_best pinned by commit.
"""

import os
import subprocess
import time

from base import Engine, Line, Result, sha256_file

TESS_CONFIG = "--oem 1 --psm 3"


class TesseractEngine(Engine):
    engine_id = "tesseract5"

    def __init__(self) -> None:
        self.config = {"lang": "eng", "config": TESS_CONFIG, "tessdata": os.environ.get("TESSDATA_PREFIX")}

    def _construct(self) -> None:
        import pytesseract
        from PIL import Image

        self._pt = pytesseract
        # Throwaway call so first-call process/page-cache cost lands in construct().
        pytesseract.image_to_data(Image.new("RGB", (64, 64), "white"), lang="eng", config=TESS_CONFIG)

    def run(self, image_rgb) -> Result:
        from PIL import Image

        image = Image.fromarray(image_rgb)
        t0 = time.perf_counter()
        data = self._pt.image_to_data(image, lang="eng", config=TESS_CONFIG, output_type=self._pt.Output.DICT)
        total_s = time.perf_counter() - t0

        groups: dict[tuple[int, int, int], list[int]] = {}
        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = float(data["conf"][i])
            if not text or conf < 0:
                continue
            groups.setdefault((data["block_num"][i], data["par_num"][i], data["line_num"][i]), []).append(i)

        lines: list[Line] = []
        for _, idxs in sorted(groups.items()):
            idxs = sorted(idxs, key=lambda i: data["word_num"][i])
            x0 = min(data["left"][i] for i in idxs)
            y0 = min(data["top"][i] for i in idxs)
            x1 = max(data["left"][i] + data["width"][i] for i in idxs)
            y1 = max(data["top"][i] + data["height"][i] for i in idxs)
            confs = [float(data["conf"][i]) for i in idxs]
            lines.append(
                Line(
                    bbox=(float(x0), float(y0), float(x1 - x0), float(y1 - y0)),
                    text=" ".join(data["text"][i].strip() for i in idxs),
                    confidence=(sum(confs) / len(confs)) / 100.0,
                )
            )
        return Result(lines=lines, total_s=total_s)

    def info(self) -> dict:
        prefix = os.environ.get("TESSDATA_PREFIX", "")
        version = subprocess.run(["tesseract", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
        commit_path = os.path.join(prefix, "COMMIT")
        commit = open(commit_path).read().strip() if os.path.exists(commit_path) else None
        import pytesseract

        return {
            "engine_id": self.engine_id,
            "engine_version": f"{version} / pytesseract {pytesseract.get_tesseract_version()}",
            "config": self.config,
            "tessdata_best_commit": commit,
            "weights_sha256": {"eng.traineddata": sha256_file(os.path.join(prefix, "eng.traineddata"))},
        }
