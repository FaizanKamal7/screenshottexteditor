import numpy as np
from PIL import Image, ImageDraw, ImageFont

from fonts.registry import FONT_REGISTRY
from stages.match import estimate_layout, iou, match_font, score_alpha
from stages.separate import separate


def _find_candidate(family: str, weight: int):
    return next(c for c in FONT_REGISTRY if c.family == family and c.weight == weight)


def _render_ground_truth(family: str, weight: int, size: float, text: str):
    """Render with PIL + the real registry font file — an independent
    rasterizer from our own skia renderer, so a passing match here is a
    real signal the matcher works, not a tautology against our own code.
    """
    candidate = _find_candidate(family, weight)
    font = ImageFont.truetype(candidate.file_path, int(size))

    probe = Image.new("RGB", (10, 10))
    text_bbox = ImageDraw.Draw(probe).textbbox((0, 0), text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    pad = 20
    canvas_w = text_w + pad * 2
    canvas_h = text_h + pad * 2

    image = Image.new("RGB", (canvas_w, canvas_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    origin = (pad - text_bbox[0], pad - text_bbox[1])
    draw.text(origin, text, fill=(15, 15, 15), font=font)

    region_bbox = (float(pad - 4), float(pad - 4), float(text_w + 8), float(text_h + 8))
    image_bgr = np.array(image)[:, :, ::-1].copy()
    return image_bgr, region_bbox


def test_score_alpha_scores_identical_masks_as_perfect():
    mask = np.zeros((20, 20), dtype=np.float32)
    mask[5:15, 5:15] = 1.0

    assert score_alpha(mask, mask) > 0.99


def test_iou_of_disjoint_masks_is_zero():
    a = np.zeros((10, 10), dtype=bool)
    a[:5, :] = True
    b = np.zeros((10, 10), dtype=bool)
    b[5:, :] = True

    assert iou(a, b) == 0.0


def test_estimate_layout_defaults_left_for_single_line():
    layout = estimate_layout([(10.0, 10.0, 100.0, 20.0)])

    assert layout.alignment == "left"
    assert layout.line_height is None


def test_match_font_recovers_known_family_and_close_size():
    text = "Settings"
    known_size = 32.0
    image_bgr, bbox = _render_ground_truth("Inter", 400, known_size, text)

    separation = separate(image_bgr, bbox)
    match = match_font(text, separation.alpha, separation.alpha.shape, bbox[3])

    assert match.family == "Inter"
    assert abs(match.size - known_size) < known_size * 0.25
    assert match.score > 0.85
    assert len(match.top_candidates) <= 3
