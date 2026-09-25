"""Engine adapter base, copied and extended from services/pipeline/bench/engines.py.

Each adapter exposes construct() (cold init, timed) and run(image_rgb) returning
a Result with per-line (bbox, text, confidence) plus whatever timing split the
library actually exposes — None where it doesn't, rather than a fabricated
number. Adapters receive already-decoded RGB uint8 pixels so every engine sees
identical pixels, and the timed region covers only the engine call.
"""

import hashlib
import os
import time
from dataclasses import dataclass, field


@dataclass
class Line:
    bbox: tuple[float, float, float, float]  # x, y, w, h in image px
    text: str
    confidence: float | None


@dataclass
class Result:
    lines: list[Line]
    total_s: float
    detect_s: float | None = None
    recognize_s: float | None = None


def quad_to_bbox(quad) -> tuple[float, float, float, float]:
    xs = [float(p[0]) for p in quad]
    ys = [float(p[1]) for p in quad]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return (x0, y0, x1 - x0, y1 - y0)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_tree(root: str) -> dict[str, str]:
    """SHA-256 of every file under root, keyed by path relative to root."""
    out: dict[str, str] = {}
    if not os.path.isdir(root):
        return out
    for dirpath, _, files in os.walk(root):
        for name in sorted(files):
            path = os.path.join(dirpath, name)
            out[os.path.relpath(path, root).replace(os.sep, "/")] = sha256_file(path)
    return dict(sorted(out.items()))


class Engine:
    engine_id: str
    config: dict = {}

    def construct(self) -> float:
        t0 = time.perf_counter()
        self._construct()
        return time.perf_counter() - t0

    def _construct(self) -> None:
        raise NotImplementedError

    def run(self, image_rgb) -> Result:
        raise NotImplementedError

    def info(self) -> dict:
        raise NotImplementedError
