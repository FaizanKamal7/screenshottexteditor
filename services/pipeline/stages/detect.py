import uuid
from dataclasses import dataclass

import cv2
import numpy as np

from ocr_engine import get_ocr_engine

BLOCK_GAP_MULTIPLIER = 1.5
BLOCK_LEFT_EDGE_TOLERANCE_PX = 8.0

# Stroke-width buckets (px) for classifying image scale. Starting heuristic —
# see docs/pipeline-tuning.md; revisit once real fixtures are available.
SCALE_1X_MAX_STROKE_PX = 2.2
SCALE_2X_MAX_STROKE_PX = 4.2


@dataclass
class DetectedLine:
    text: str
    bbox: tuple[float, float, float, float]  # x, y, w, h
    confidence: float
    block_id: str


@dataclass
class DetectResult:
    lines: list[DetectedLine]


def _quad_to_bbox(quad: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return (x0, y0, x1 - x0, y1 - y0)


def group_into_blocks(
    boxed_lines: list[dict],
) -> list[DetectedLine]:
    """Assign block ids to lines already sorted top-to-bottom, left-to-right.

    Pure function (no OCR dependency) so the grouping heuristic can be
    unit-tested with synthetic bboxes.
    """
    sorted_lines = sorted(boxed_lines, key=lambda line: (line["bbox"][1], line["bbox"][0]))

    heights = [line["bbox"][3] for line in sorted_lines if line["bbox"][3] > 0]
    median_height = float(np.median(heights)) if heights else 16.0

    lines: list[DetectedLine] = []
    block_id = ""
    prev_bottom: float | None = None
    prev_left: float | None = None

    for line in sorted_lines:
        x, y, w, h = line["bbox"]
        starts_new_block = prev_bottom is None
        if prev_bottom is not None and prev_left is not None:
            gap = y - prev_bottom
            left_shift = abs(x - prev_left)
            starts_new_block = gap > BLOCK_GAP_MULTIPLIER * median_height or left_shift > BLOCK_LEFT_EDGE_TOLERANCE_PX

        if starts_new_block:
            block_id = str(uuid.uuid4())

        lines.append(
            DetectedLine(text=line["text"], bbox=line["bbox"], confidence=line["confidence"], block_id=block_id)
        )
        prev_bottom = y + h
        prev_left = x

    return lines


def detect(image_bgr: np.ndarray) -> DetectResult:
    engine = get_ocr_engine()
    raw_lines = engine.run(image_bgr)

    boxed = [
        {"text": raw.text, "bbox": _quad_to_bbox(raw.quad), "confidence": raw.confidence} for raw in raw_lines
    ]
    lines = group_into_blocks(boxed)

    return DetectResult(lines=lines)


def estimate_scale_factor(masks: list[np.ndarray]) -> int:
    stroke_widths: list[float] = []

    for mask in masks:
        binary = (mask > 0.5).astype(np.uint8)
        if binary.sum() == 0:
            continue
        dist = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
        nonzero = dist[dist > 0]
        if nonzero.size == 0:
            continue
        # stroke width ~= 2x the distance from a stroke-interior pixel to its nearest edge
        stroke_widths.append(float(np.percentile(nonzero, 90)) * 2)

    if not stroke_widths:
        return 1

    modal_width = float(np.median(stroke_widths))
    if modal_width < SCALE_1X_MAX_STROKE_PX:
        return 1
    if modal_width < SCALE_2X_MAX_STROKE_PX:
        return 2
    return 3
