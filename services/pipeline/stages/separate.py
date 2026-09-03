import base64
from dataclasses import dataclass

import cv2
import numpy as np

from models import CharBox

FLAT_BACKGROUND_VARIANCE_THRESHOLD = 15.0
MIN_INK_COLUMN_FRACTION = 0.08
MAX_CHAR_GAP_PX = 2
CROP_PADDING_PX = 3


@dataclass
class SeparationResult:
    alpha: np.ndarray  # float32, HxW, 0..1
    bg_variance: float
    char_boxes: list[CharBox]
    alpha_mask_png: str
    crop_bbox: tuple[int, int, int, int]  # x0, y0, x1, y1 in absolute image coords; matches alpha.shape


def _border_ring_variance(gray: np.ndarray, ring_px: int = 2) -> float:
    h, w = gray.shape
    ring_px = min(ring_px, h // 2, w // 2) or 1
    mask = np.zeros_like(gray, dtype=bool)
    mask[:ring_px, :] = True
    mask[-ring_px:, :] = True
    mask[:, :ring_px] = True
    mask[:, -ring_px:] = True
    return float(np.var(gray[mask].astype(np.float64)))


def _flat_background_alpha(crop_bgr: np.ndarray, gray: np.ndarray, bg_variance_ring_px: int = 2) -> np.ndarray:
    h, w = gray.shape
    ring_px = min(bg_variance_ring_px, h // 2, w // 2) or 1
    border_mask = np.zeros_like(gray, dtype=bool)
    border_mask[:ring_px, :] = True
    border_mask[-ring_px:, :] = True
    border_mask[:, :ring_px] = True
    border_mask[:, -ring_px:] = True
    bg_color = np.median(crop_bgr[border_mask].astype(np.float64), axis=0)

    # Otsu on grayscale is only used to pick out *which* pixels are text, not
    # to measure how "text-like" each one is — that classification step is
    # still fine on luminance alone.
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    foreground_a = otsu == 255
    foreground_b = otsu == 0
    # smaller-area class is text
    text_mask = foreground_a if foreground_a.sum() < foreground_b.sum() else foreground_b
    if not text_mask.any():
        return np.zeros_like(gray, dtype=np.float32)

    text_color = np.median(crop_bgr[text_mask].astype(np.float64), axis=0)

    # Project each pixel's full BGR color onto the bg->text color axis,
    # rather than collapsing to grayscale luminance first. A saturated but
    # light text color (e.g. yellow on a white background) can sit almost on
    # top of the background in luminance alone while still being clearly
    # distinct in color — collapsing to gray shrinks the denominator below
    # and amplifies ordinary compression/anti-aliasing noise into a
    # thicker-than-real "ink" mask. That artificially thickened mask is what
    # let stage 3's font matcher (see RESTART_CONFIGS in stages/match.py)
    # settle on a bolder weight than the source text actually used, for any
    # text color that isn't near-black.
    axis = text_color - bg_color
    denom = max(float(np.dot(axis, axis)), 1.0)
    diff = crop_bgr.astype(np.float64) - bg_color
    projection = diff.reshape(-1, 3) @ axis / denom
    alpha = projection.reshape(h, w).astype(np.float32)
    return np.clip(alpha, 0.0, 1.0)


def _kmeans_alpha(crop_bgr: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2LAB)
    h, w = lab.shape[:2]
    samples = lab.reshape(-1, 3).astype(np.float32)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    _, labels, _ = cv2.kmeans(samples, 2, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    labels = labels.reshape(h, w)

    count0 = int(np.sum(labels == 0))
    count1 = int(np.sum(labels == 1))
    text_label = 0 if count0 < count1 else 1
    hard_mask = (labels == text_label).astype(np.float32)

    soft_mask = cv2.GaussianBlur(hard_mask, (3, 3), sigmaX=0.6)
    return np.clip(soft_mask, 0.0, 1.0)


def _char_boxes_from_alpha(alpha: np.ndarray, origin_x: int, origin_y: int, region_h: int) -> list[CharBox]:
    h, w = alpha.shape
    column_ink = alpha.sum(axis=0)
    threshold = MIN_INK_COLUMN_FRACTION * h
    is_ink = column_ink > threshold

    boxes: list[CharBox] = []
    run_start: int | None = None
    gap = 0
    for col in range(w):
        if is_ink[col]:
            if run_start is None:
                run_start = col
            gap = 0
        else:
            if run_start is not None:
                gap += 1
                if gap > MAX_CHAR_GAP_PX:
                    run_end = col - gap
                    boxes.append(
                        CharBox(
                            x=float(origin_x + run_start),
                            y=float(origin_y),
                            w=float(run_end - run_start + 1),
                            h=float(region_h),
                        )
                    )
                    run_start = None
                    gap = 0
    if run_start is not None:
        run_end = w - 1 - gap
        if run_end >= run_start:
            boxes.append(
                CharBox(
                    x=float(origin_x + run_start),
                    y=float(origin_y),
                    w=float(run_end - run_start + 1),
                    h=float(region_h),
                )
            )
    return boxes


def _encode_alpha_png(alpha: np.ndarray) -> str:
    as_uint8 = (alpha * 255).astype(np.uint8)
    ok, buffer = cv2.imencode(".png", as_uint8)
    if not ok:
        return ""
    return base64.b64encode(buffer.tobytes()).decode("ascii")


def separate(image_bgr: np.ndarray, bbox: tuple[float, float, float, float]) -> SeparationResult:
    img_h, img_w = image_bgr.shape[:2]
    x, y, w, h = bbox
    x0 = max(int(x) - CROP_PADDING_PX, 0)
    y0 = max(int(y) - CROP_PADDING_PX, 0)
    x1 = min(int(x + w) + CROP_PADDING_PX, img_w)
    y1 = min(int(y + h) + CROP_PADDING_PX, img_h)

    crop = image_bgr[y0:y1, x0:x1]
    if crop.size == 0:
        empty = np.zeros((1, 1), dtype=np.float32)
        return SeparationResult(
            alpha=empty, bg_variance=0.0, char_boxes=[], alpha_mask_png="", crop_bbox=(x0, y0, x1, y1)
        )

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    bg_variance = _border_ring_variance(gray)

    if bg_variance < FLAT_BACKGROUND_VARIANCE_THRESHOLD:
        alpha = _flat_background_alpha(crop, gray)
    else:
        alpha = _kmeans_alpha(crop)

    char_boxes = _char_boxes_from_alpha(alpha, origin_x=x0, origin_y=int(y), region_h=int(h))
    alpha_mask_png = _encode_alpha_png(alpha)

    return SeparationResult(
        alpha=alpha,
        bg_variance=bg_variance,
        char_boxes=char_boxes,
        alpha_mask_png=alpha_mask_png,
        crop_bbox=(x0, y0, x1, y1),
    )
