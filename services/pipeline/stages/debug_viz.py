import base64

import cv2
import numpy as np

from stages.erase import clean_inpaint_mask

# How far around `crop_bbox` to include in the debug tile, so the rectangle
# and mask overlay are visible against real surrounding pixels instead of
# being cropped flush to their own edges.
CONTEXT_PADDING_PX = 12

OCR_BBOX_COLOR_BGR = (0, 200, 0)  # green: the raw OCR-detected line bbox
CROP_BBOX_COLOR_BGR = (0, 200, 255)  # amber: the padded crop actually erased/inpainted
MASK_COLOR_BGR = (0, 0, 255)  # red: pixels clean_inpaint_mask will actually touch
MASK_OVERLAY_ALPHA = 0.55


def render_debug_overlay(
    image_bgr: np.ndarray,
    ocr_bbox: tuple[float, float, float, float] | None,
    crop_bbox: tuple[int, int, int, int],
    alpha: np.ndarray,
) -> str:
    """Renders a small tile around `crop_bbox` showing exactly what one edit
    will touch: the raw OCR bbox (green), the padded crop passed to erase()
    (amber), and the precise glyph mask that will actually be reconstructed
    (red, semi-transparent) — so mask/bbox precision can be checked visually
    instead of inferred from the final composited image.

    Returns a base64-encoded PNG. Not part of the normal request path; only
    computed when a caller explicitly asks for debug output (see main.py's
    `debug` flag), since it does real extra drawing work per region.
    """
    img_h, img_w = image_bgr.shape[:2]
    cx0, cy0, cx1, cy1 = crop_bbox

    tx0 = max(0, cx0 - CONTEXT_PADDING_PX)
    ty0 = max(0, cy0 - CONTEXT_PADDING_PX)
    tx1 = min(img_w, cx1 + CONTEXT_PADDING_PX)
    ty1 = min(img_h, cy1 + CONTEXT_PADDING_PX)

    tile = image_bgr[ty0:ty1, tx0:tx1].copy()
    if tile.size == 0:
        tile = np.full((1, 1, 3), 255, dtype=np.uint8)
        ok, buffer = cv2.imencode(".png", tile)
        return base64.b64encode(buffer.tobytes()).decode("ascii") if ok else ""

    mask = clean_inpaint_mask(alpha)
    if mask.size and mask.shape == (cy1 - cy0, cx1 - cx0):
        overlay = tile.copy()
        # Mask coords are relative to crop_bbox; offset into the padded tile.
        oy0, ox0 = cy0 - ty0, cx0 - tx0
        oy1, ox1 = oy0 + mask.shape[0], ox0 + mask.shape[1]
        region = overlay[oy0:oy1, ox0:ox1]
        region[mask.astype(bool)] = MASK_COLOR_BGR
        cv2.addWeighted(overlay, MASK_OVERLAY_ALPHA, tile, 1 - MASK_OVERLAY_ALPHA, 0, dst=tile)

    cv2.rectangle(tile, (cx0 - tx0, cy0 - ty0), (cx1 - tx0 - 1, cy1 - ty0 - 1), CROP_BBOX_COLOR_BGR, 1)

    if ocr_bbox is not None:
        ox, oy, ow, oh = ocr_bbox
        p0 = (int(ox) - tx0, int(oy) - ty0)
        p1 = (int(ox + ow) - tx0, int(oy + oh) - ty0)
        cv2.rectangle(tile, p0, p1, OCR_BBOX_COLOR_BGR, 1)

    ok, buffer = cv2.imencode(".png", tile)
    return base64.b64encode(buffer.tobytes()).decode("ascii") if ok else ""
