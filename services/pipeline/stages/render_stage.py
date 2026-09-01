from dataclasses import dataclass

import numpy as np

from models import BackgroundFill
from renderer import measure_text_width, render_text
from stages.erase import erase, fill_array

# Reflow policy, per the brief's stage 5. 'expand' is the default: replacement
# text keeps the caller's font size and the box grows to fit it instead of
# shrinking the font. 'wrap'/'truncate' still need layout awareness (siblings,
# surrounding element bounds) that stage 3 doesn't capture yet — left for a
# follow-up. Shrinking (`fit_font_size`, `MIN_SHRINK_RATIO`) is now only a
# last-resort fallback for when even growing to the image edge isn't enough
# room — it no longer runs on every over-length edit.
MIN_SHRINK_RATIO = 0.5


@dataclass
class ComposeResult:
    image_bgr: np.ndarray
    font_size: float
    overflowed: bool  # True if even the size floor didn't fit — caller should flag low confidence


def fit_font_size(text: str, font_path: str, size_px: float, letter_spacing_px: float, max_width: float) -> tuple[float, bool]:
    """Shrinks `size_px` until `text` fits `max_width`, down to a floor. Returns (size, overflowed)."""
    width = measure_text_width(text, font_path, size_px, letter_spacing_px)
    if width <= max_width or width == 0:
        return size_px, False

    floor = size_px * MIN_SHRINK_RATIO
    fitted = size_px * (max_width / width)
    if fitted >= floor:
        return fitted, False

    return floor, True


def _expanded_bbox(
    alignment: str,
    crop_bbox: tuple[int, int, int, int],
    natural_text_width: float,
    image_width: int,
) -> tuple[int, int, int, int]:
    """Grows `crop_bbox` horizontally to fit `natural_text_width` — the text
    measured at the caller's original, unshrunk font size — instead of
    shrinking the font. Clamped to the image's own bounds; doesn't know about
    sibling UI elements, so `fit_font_size` downstream is still the safety
    net for the rare case where even the image edge isn't enough room.
    """
    x0, y0, x1, y1 = crop_bbox
    available = x1 - x0
    extra = natural_text_width - available
    if extra <= 0:
        return crop_bbox

    if alignment == "right":
        new_x0 = max(0.0, x0 - extra)
        return (int(new_x0), y0, x1, y1)

    if alignment == "center":
        half = extra / 2
        new_x0 = max(0.0, x0 - half)
        # Whatever the left side couldn't take (clamped at the image edge)
        # goes to the right side instead of being lost.
        leftover = half - (x0 - new_x0)
        new_x1 = min(float(image_width), x1 + half + max(0.0, leftover))
        return (int(new_x0), y0, int(new_x1), y1)

    # 'left' (the common case): anchor the left edge in place, grow rightward.
    new_x1 = min(float(image_width), x1 + extra)
    return (x0, y0, int(new_x1), y1)


def _translate_bbox(
    bbox: tuple[int, int, int, int],
    offset_x: float,
    offset_y: float,
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    """Shifts `bbox` by a "slight nudge" (drag or Alt+Arrow in the editor),
    keeping its size fixed and clamping so it stays fully on the image.
    """
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    new_x0 = max(0.0, min(float(x0) + offset_x, float(image_width - w)))
    new_y0 = max(0.0, min(float(y0) + offset_y, float(image_height - h)))
    return (int(new_x0), int(new_y0), int(new_x0) + w, int(new_y0) + h)


def _x_offset_for_alignment(alignment: str, available_width: float, text_width: float, base_x_offset: float) -> float:
    if alignment == "center":
        return (available_width - text_width) / 2
    if alignment == "right":
        return available_width - text_width
    # 'left': anchor at the fitted left-bearing (stage 3's x_offset), not the
    # crop's bare edge — see X_OFFSET_SEARCH_PX in stages/match.py for why.
    return base_x_offset


def compose_region(
    image_bgr: np.ndarray,
    crop_bbox: tuple[int, int, int, int],
    alpha: np.ndarray,
    background: BackgroundFill | None,
    text: str,
    font_path: str,
    font_size: float,
    letter_spacing: float,
    baseline_local_y: float,
    text_color: tuple[int, int, int],
    alignment: str,
    base_x_offset: float = 0.0,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> ComposeResult:
    """Erases the original glyphs in `crop_bbox`, then draws `text` in their place.

    `baseline_local_y`, `base_x_offset`, and the crop's width/height are all
    relative to `crop_bbox`, matching stages/match.py's rendering convention
    so a same-text round trip reproduces the original placement. If `text` is
    wider than `crop_bbox` at `font_size`, the box grows to fit it (see
    `_expanded_bbox`) rather than the font shrinking — shrinking only kicks
    in if growth alone, out to the image edge, still isn't enough. `offset_x`/
    `offset_y` then shift the whole (possibly-expanded) box by a slight
    manual nudge — a drag or Alt+Arrow in the editor — still clamped to the
    image bounds.
    """
    x0, y0, x1, y1 = crop_bbox
    width, height = x1 - x0, y1 - y0

    erased = erase(image_bgr, crop_bbox, alpha, background)
    if width <= 0 or height <= 0:
        return ComposeResult(image_bgr=erased, font_size=font_size, overflowed=False)

    image_width = image_bgr.shape[1]
    image_height = image_bgr.shape[0]
    natural_width = measure_text_width(text, font_path, font_size, letter_spacing)
    ex0, ey0, ex1, ey1 = _expanded_bbox(alignment, crop_bbox, natural_width, image_width)
    expanded_width = ex1 - ex0

    # The expansion strip(s) never had old glyphs in them — there's nothing
    # to erase, just fill them with the same background the original crop
    # was erased to.
    if ex0 < x0:
        strip_w = x0 - ex0
        erased[ey0:ey1, ex0:x0] = np.clip(fill_array(background, ey1 - ey0, strip_w), 0, 255).astype(np.uint8)
    if ex1 > x1:
        strip_w = ex1 - x1
        erased[ey0:ey1, x1:ex1] = np.clip(fill_array(background, ey1 - ey0, strip_w), 0, 255).astype(np.uint8)

    fx0, fy0, fx1, fy1 = _translate_bbox((ex0, ey0, ex1, ey1), offset_x, offset_y, image_width, image_height)
    if (fx0, fy0, fx1, fy1) != (ex0, ey0, ex1, ey1):
        # A nudge lands the box somewhere the erase/expand fill above never
        # touched — flood-fill the whole destination rather than working out
        # the exact (possibly L-shaped) overlap with what's already clean.
        erased[fy0:fy1, fx0:fx1] = np.clip(fill_array(background, fy1 - fy0, fx1 - fx0), 0, 255).astype(np.uint8)

    fitted_size, overflowed = fit_font_size(text, font_path, font_size, letter_spacing, float(expanded_width))
    text_width = measure_text_width(text, font_path, fitted_size, letter_spacing)
    x_offset = _x_offset_for_alignment(alignment, float(expanded_width), text_width, base_x_offset)

    new_alpha = render_text(text, font_path, fitted_size, letter_spacing, (x_offset, baseline_local_y), (expanded_width, height))

    crop = erased[fy0:fy1, fx0:fx1].astype(np.float32)
    color_bgr = np.array([text_color[2], text_color[1], text_color[0]], dtype=np.float32)
    weight = new_alpha[..., None]
    blended = crop * (1.0 - weight) + color_bgr * weight
    erased[fy0:fy1, fx0:fx1] = np.clip(blended, 0, 255).astype(np.uint8)

    return ComposeResult(image_bgr=erased, font_size=fitted_size, overflowed=overflowed)
