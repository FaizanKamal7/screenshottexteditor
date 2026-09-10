import cv2
import numpy as np

from models import BackgroundFill

# BackgroundFill ('flat' / 'gradient', see stages/match.py's estimate_color)
# is only used to invent pixels where none exist in the source image — the
# expansion strip(s) render_stage.py adds when replacement text is wider
# than the original crop (see compose_region) — and as a last-resort fill
# when a crop's mask covers it edge-to-edge (see erase() below). It is
# deliberately NOT used to reconstruct the background under the erased
# glyphs anymore: painting a flat color or a 2-stop gradient over the whole
# crop rectangle discarded real texture and any content the mask
# over-included, which is what produced the reported gray/blurred wash and
# smearing on nearby content. That reconstruction is now cv2.inpaint,
# restricted to the actual (cleaned) glyph mask — see _clean_inpaint_mask.


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


# A pixel needs to clear this before it's treated as "definitely glyph ink"
# for erasure — higher than separate.py's own soft-alpha values so faint
# anti-aliasing/compression noise near the mask boundary doesn't get pulled
# into the inpaint mask. Real inpainting doesn't need the soft fringe
# included: cv2.inpaint blends from the reconstructed interior outward, so
# leaving a 1px unmasked band of faint old-glyph color at the very edge
# still disappears once dilated back in below.
MASK_ALPHA_THRESHOLD = 0.35

# Isolated speckles below this pixel count are near-certainly a false
# positive from separate.py's classifiers (e.g. _kmeans_alpha finding a
# stray pixel that happens to match the "text" color cluster), not a real
# glyph fragment — even the thinnest legitimate stroke spans more pixels
# than this once anti-aliased. Dropped via connected-component area, not a
# blanket morphological opening, so genuinely thin (1-2px) strokes aren't
# eroded away along with the noise.
MIN_INK_COMPONENT_PX = 2

# cv2.inpaint's search radius in source pixels. Small on purpose: erasure
# only needs to reconstruct a thin band around each glyph stroke, and a
# larger radius risks pulling in unrelated content near the mask boundary.
INPAINT_RADIUS_PX = 3


def clean_inpaint_mask(alpha: np.ndarray) -> np.ndarray:
    """Binarize `alpha` into a glyph-shaped 8-bit (0/1) mask for cv2.inpaint.

    Precise by construction: this only marks pixels the mask actually
    considers ink (plus a 1px dilation to fully cover anti-aliased fringes),
    never the bounding rectangle around them. Background pixels adjacent to
    a glyph — even one pixel away — are never in this mask and are never
    touched by erase() below. Also used by stages/debug_viz.py to visualize
    exactly which pixels a given edit will touch.
    """
    hard = (alpha > MASK_ALPHA_THRESHOLD).astype(np.uint8)
    if not hard.any():
        return hard

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(hard, connectivity=8)
    cleaned = np.zeros_like(hard)
    for label in range(1, num_labels):
        if stats[label, cv2.CC_STAT_AREA] >= MIN_INK_COMPONENT_PX:
            cleaned[labels == label] = 1

    kernel = np.ones((3, 3), np.uint8)
    return cv2.dilate(cleaned, kernel, iterations=1)


def erase(
    image_bgr: np.ndarray,
    crop_bbox: tuple[int, int, int, int],
    alpha: np.ndarray,
    background: BackgroundFill | None,
) -> np.ndarray:
    """Returns a copy of `image_bgr` with the glyphs inside `crop_bbox` erased.

    Reconstruction is mask-driven (cv2.inpaint), not a rectangle fill: only
    pixels `_clean_inpaint_mask` marks as glyph ink are ever written, using
    their real neighboring pixels to rebuild whatever texture/gradient the
    background actually has. Every other pixel — including background
    immediately next to a glyph, and any other text elsewhere in the crop —
    passes through byte-for-byte unchanged.

    The one case with no real background to reconstruct from is a mask that
    covers the crop edge-to-edge (glyphs fill the whole assigned region,
    leaving no unmasked pixel for inpainting to source texture from) — that
    still falls back to `fill_array`'s fitted flat/gradient guess, same as
    the old behavior, since there is nothing else to go on.
    """
    x0, y0, x1, y1 = crop_bbox
    out = image_bgr.copy()
    crop = out[y0:y1, x0:x1]
    if crop.size == 0:
        return out

    inpaint_mask = clean_inpaint_mask(alpha)
    if not inpaint_mask.any():
        return out

    if inpaint_mask.all():
        fill = fill_array(background, crop.shape[0], crop.shape[1])
        out[y0:y1, x0:x1] = np.clip(fill, 0, 255).astype(np.uint8)
        return out

    reconstructed = cv2.inpaint(crop, inpaint_mask * 255, INPAINT_RADIUS_PX, cv2.INPAINT_TELEA)
    out[y0:y1, x0:x1] = reconstructed
    return out
