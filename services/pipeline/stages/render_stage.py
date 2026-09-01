from dataclasses import dataclass

import numpy as np

from models import BackgroundFill
from renderer import measure_text_width, render_text
from stages.erase import erase

# Reflow policy, per the brief's stage 5: only 'shrink' is implemented today
# (default for constrained UI elements). 'expand'/'wrap'/'truncate' need
# layout awareness (siblings, surrounding element bounds) that stage 3
# doesn't capture yet — left for a follow-up rather than faked here.
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
) -> ComposeResult:
    """Erases the original glyphs in `crop_bbox`, then draws `text` in their place.

    `baseline_local_y`, `base_x_offset`, and the crop's width/height are all
    relative to `crop_bbox`, matching stages/match.py's rendering convention
    so a same-text round trip reproduces the original placement.
    """
    x0, y0, x1, y1 = crop_bbox
    width, height = x1 - x0, y1 - y0

    erased = erase(image_bgr, crop_bbox, alpha, background)
    if width <= 0 or height <= 0:
        return ComposeResult(image_bgr=erased, font_size=font_size, overflowed=False)

    fitted_size, overflowed = fit_font_size(text, font_path, font_size, letter_spacing, float(width))
    text_width = measure_text_width(text, font_path, fitted_size, letter_spacing)
    x_offset = _x_offset_for_alignment(alignment, float(width), text_width, base_x_offset)

    new_alpha = render_text(text, font_path, fitted_size, letter_spacing, (x_offset, baseline_local_y), (width, height))

    crop = erased[y0:y1, x0:x1].astype(np.float32)
    color_bgr = np.array([text_color[2], text_color[1], text_color[0]], dtype=np.float32)
    weight = new_alpha[..., None]
    blended = crop * (1.0 - weight) + color_bgr * weight
    erased[y0:y1, x0:x1] = np.clip(blended, 0, 255).astype(np.uint8)

    return ComposeResult(image_bgr=erased, font_size=fitted_size, overflowed=overflowed)
