import numpy as np

from models import BackgroundFill

# BackgroundFill only models 'flat' and 'gradient' today (stages/match.py's
# estimate_color falls back to a fitted gradient for any non-flat crop, textured
# backgrounds included) — so those are the only two fills this stage handles.
# A textured/photo branch (LaMa inpainting, per the brief) is a real gap, not
# an oversight: it needs stage 3 to actually classify "textured" separately
# from "gradient" first.


def _flat_fill(color: tuple[int, int, int], height: int, width: int) -> np.ndarray:
    bgr = np.array([color[2], color[1], color[0]], dtype=np.float32)
    return np.tile(bgr, (height, width, 1))


def _gradient_fill(background: BackgroundFill, height: int, width: int) -> np.ndarray:
    if len(background.stops) < 2:
        color = background.stops[0].color if background.stops else (255, 255, 255)
        return _flat_fill(color, height, width)

    angle = np.radians(background.angle_deg or 0.0)
    direction_x, direction_y = np.cos(angle), np.sin(angle)
    ys, xs = np.mgrid[0:height, 0:width]
    projection = xs * direction_x + ys * direction_y

    proj_min, proj_max = float(projection.min()), float(projection.max())
    denom = max(proj_max - proj_min, 1e-6)
    t = (projection - proj_min) / denom

    stops = sorted(background.stops, key=lambda s: s.position)
    start_bgr = np.array([stops[0].color[2], stops[0].color[1], stops[0].color[0]], dtype=np.float32)
    end_bgr = np.array([stops[-1].color[2], stops[-1].color[1], stops[-1].color[0]], dtype=np.float32)

    t3 = t[..., None]
    return start_bgr + (end_bgr - start_bgr) * t3


def fill_array(background: BackgroundFill | None, height: int, width: int) -> np.ndarray:
    """BGR float32 fill for a crop of the given size, per the background's fitted model."""
    if background is None or background.kind == "flat":
        color = background.color if background and background.color else (255, 255, 255)
        return _flat_fill(color, height, width)
    return _gradient_fill(background, height, width)


# Any pixel the separation mask considers even lightly "text" gets fully
# erased rather than proportionally blended. A pure linear alpha blend looks
# principled but is wrong for erasure specifically: it leaves the old glyph's
# anti-aliased halo — every edge pixel at, say, 40% mask coverage — visibly
# ghosted at 40% strength, which reads as a shadow of the deleted/replaced
# text. The new text drawn on top afterwards supplies its own anti-aliasing,
# so the erase step doesn't need to preserve soft edges; it needs to be
# clean. Only near-zero-alpha pixels (true background, not text) stay a
# proportional (effectively no-op) blend.
ERASE_ALPHA_FLOOR = 0.05


def erase(
    image_bgr: np.ndarray,
    crop_bbox: tuple[int, int, int, int],
    alpha: np.ndarray,
    background: BackgroundFill | None,
) -> np.ndarray:
    """Returns a copy of `image_bgr` with the glyphs inside `crop_bbox` erased."""
    x0, y0, x1, y1 = crop_bbox
    out = image_bgr.copy()
    crop = out[y0:y1, x0:x1].astype(np.float32)
    if crop.size == 0:
        return out

    fill = fill_array(background, crop.shape[0], crop.shape[1])
    hardened_alpha = np.where(alpha > ERASE_ALPHA_FLOOR, 1.0, alpha).astype(np.float32)
    weight = hardened_alpha[..., None]
    blended = crop * (1.0 - weight) + fill * weight
    out[y0:y1, x0:x1] = np.clip(blended, 0, 255).astype(np.uint8)
    return out
