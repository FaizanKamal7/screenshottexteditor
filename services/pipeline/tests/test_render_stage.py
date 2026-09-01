import numpy as np
from PIL import Image, ImageDraw, ImageFont

from fonts.registry import FONT_REGISTRY
from models import BackgroundFill
from stages.render_stage import _expanded_bbox, _translate_bbox, compose_region, fit_font_size
from stages.separate import separate


def _find_font_path(family: str, weight: int) -> str:
    return next(c.file_path for c in FONT_REGISTRY if c.family == family and c.weight == weight)


def _render_ground_truth(text: str, size: float = 32.0):
    font_path = _find_font_path("Inter", 400)
    font = ImageFont.truetype(font_path, int(size))

    probe = Image.new("RGB", (10, 10))
    text_bbox = ImageDraw.Draw(probe).textbbox((0, 0), text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    pad = 20
    canvas_w, canvas_h = text_w + pad * 2, text_h + pad * 2
    image = Image.new("RGB", (canvas_w, canvas_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    origin = (pad - text_bbox[0], pad - text_bbox[1])
    draw.text(origin, text, fill=(15, 15, 15), font=font)

    bbox = (float(pad - 4), float(pad - 4), float(text_w + 8), float(text_h + 8))
    return np.array(image)[:, :, ::-1].copy(), bbox


def test_fit_font_size_returns_original_size_when_text_already_fits():
    font_path = _find_font_path("Inter", 400)

    size, overflowed = fit_font_size("Hi", font_path, 20.0, 0.0, max_width=500.0)

    assert size == 20.0
    assert overflowed is False


def test_fit_font_size_shrinks_long_replacement_text_to_fit():
    font_path = _find_font_path("Inter", 400)
    narrow_width = 40.0

    size, overflowed = fit_font_size("A much longer replacement string", font_path, 20.0, 0.0, max_width=narrow_width)

    assert size < 20.0
    assert overflowed is True  # even the floor won't fit this much text in this little space


def test_expanded_bbox_returns_original_when_text_already_fits():
    result = _expanded_bbox("left", (10, 10, 60, 30), natural_text_width=40.0, image_width=200)

    assert result == (10, 10, 60, 30)


def test_expanded_bbox_grows_right_for_left_aligned_overflow():
    # Available width is 50 (60-10); text needs 90 -> 40px short.
    result = _expanded_bbox("left", (10, 10, 60, 30), natural_text_width=90.0, image_width=200)

    assert result == (10, 10, 100, 30)  # left edge unchanged, right edge pushed out by the shortfall


def test_expanded_bbox_grows_left_for_right_aligned_overflow():
    result = _expanded_bbox("right", (100, 10, 150, 30), natural_text_width=90.0, image_width=200)

    assert result == (60, 10, 150, 30)  # right edge unchanged, left edge pushed out by the shortfall


def test_expanded_bbox_grows_both_sides_for_centered_overflow():
    result = _expanded_bbox("center", (80, 10, 120, 30), natural_text_width=80.0, image_width=200)

    assert result == (60, 10, 140, 30)  # 40px short, split 20/20 either side


def test_expanded_bbox_clamps_to_image_bounds_and_gives_leftover_to_the_other_side():
    # Centered, near the left edge: the left side can only give up 5px before
    # hitting x=0, so the right side has to make up the rest of the 40px need.
    result = _expanded_bbox("center", (5, 10, 45, 30), natural_text_width=80.0, image_width=200)

    x0, y0, x1, y1 = result
    assert x0 == 0
    assert (x1 - x0) >= 80.0  # still wide enough for the text despite the clamp


def test_translate_bbox_shifts_by_the_requested_offset():
    result = _translate_bbox((20, 30, 60, 50), offset_x=15.0, offset_y=-10.0, image_width=200, image_height=200)

    assert result == (35, 20, 75, 40)  # same 40x20 size, just moved


def test_translate_bbox_preserves_size_when_clamped_at_image_edges():
    # Dragging far past the top-left edge — position clamps to 0, but the
    # box's own size must stay exactly what it was, not get cropped.
    result = _translate_bbox((20, 30, 60, 50), offset_x=-500.0, offset_y=-500.0, image_width=200, image_height=200)

    x0, y0, x1, y1 = result
    assert (x0, y0) == (0, 0)
    assert (x1 - x0, y1 - y0) == (40, 20)


def test_translate_bbox_clamps_at_the_far_edge_too():
    result = _translate_bbox((20, 30, 60, 50), offset_x=500.0, offset_y=500.0, image_width=200, image_height=200)

    x0, y0, x1, y1 = result
    assert (x1, y1) == (200, 200)
    assert (x1 - x0, y1 - y0) == (40, 20)


def test_translate_bbox_no_offset_is_a_no_op():
    bbox = (20, 30, 60, 50)
    result = _translate_bbox(bbox, offset_x=0.0, offset_y=0.0, image_width=200, image_height=200)

    assert result == bbox


def test_compose_region_round_trip_reproduces_similar_appearance():
    text = "Settings"
    image_bgr, bbox = _render_ground_truth(text)
    separation = separate(image_bgr, bbox)

    font_path = _find_font_path("Inter", 400)
    background = BackgroundFill(kind="flat", color=(255, 255, 255))
    baseline_local_y = separation.alpha.shape[0] * 0.8

    result = compose_region(
        image_bgr,
        separation.crop_bbox,
        separation.alpha,
        background,
        text,
        font_path,
        font_size=32.0,
        letter_spacing=0.0,
        baseline_local_y=baseline_local_y,
        text_color=(15, 15, 15),
        alignment="left",
    )

    x0, y0, x1, y1 = separation.crop_bbox
    patch = result.image_bgr[y0:y1, x0:x1]
    # Same text redrawn onto its own erased slot should still look like ink on
    # a light background, not a blank rectangle or noise.
    assert patch.std() > 5.0
    assert result.overflowed is False


def test_compose_region_grows_box_instead_of_shrinking_font_for_longer_text():
    # Unlike _render_ground_truth's tightly-fitted canvas, this one has a lot
    # of blank room to the right of "Settings" so growth isn't immediately
    # clamped by the image edge — otherwise the fallback shrink would kick in
    # for the same reason it should for a genuinely too-small image.
    text = "Settings"
    image_bgr, bbox = _render_ground_truth(text)
    tight_h, tight_w = image_bgr.shape[:2]
    wide_canvas = np.full((tight_h, tight_w + 400, 3), 255, dtype=np.uint8)
    wide_canvas[:, :tight_w] = image_bgr

    separation = separate(wide_canvas, bbox)

    font_path = _find_font_path("Inter", 400)
    background = BackgroundFill(kind="flat", color=(255, 255, 255))
    baseline_local_y = separation.alpha.shape[0] * 0.8

    longer_text = "Settings and Notifications"
    result = compose_region(
        wide_canvas,
        separation.crop_bbox,
        separation.alpha,
        background,
        longer_text,
        font_path,
        font_size=32.0,
        letter_spacing=0.0,
        baseline_local_y=baseline_local_y,
        text_color=(15, 15, 15),
        alignment="left",
    )

    assert result.font_size == 32.0  # unchanged — the box grew instead
    assert result.overflowed is False

    # Growth shows up as: pixels well past the original crop's right edge —
    # previously blank white canvas — now have ink drawn on them.
    x0, y0, x1, y1 = separation.crop_bbox
    strip_past_original_edge = slice(x1, x1 + 100)
    assert not np.array_equal(
        result.image_bgr[y0:y1, strip_past_original_edge],
        wide_canvas[y0:y1, strip_past_original_edge],
    )


def test_compose_region_nudge_draws_at_the_shifted_position_not_the_original():
    text = "Settings"
    image_bgr, bbox = _render_ground_truth(text)
    tight_h, tight_w = image_bgr.shape[:2]
    # Extra room on every side so a diagonal nudge has somewhere to land.
    padded = np.full((tight_h + 200, tight_w + 200, 3), 255, dtype=np.uint8)
    padded[100 : 100 + tight_h, 100 : 100 + tight_w] = image_bgr
    bx, by, bw, bh = bbox
    shifted_bbox = (bx + 100, by + 100, bw, bh)

    separation = separate(padded, shifted_bbox)
    font_path = _find_font_path("Inter", 400)
    background = BackgroundFill(kind="flat", color=(255, 255, 255))
    baseline_local_y = separation.alpha.shape[0] * 0.8

    result = compose_region(
        padded,
        separation.crop_bbox,
        separation.alpha,
        background,
        text,
        font_path,
        font_size=32.0,
        letter_spacing=0.0,
        baseline_local_y=baseline_local_y,
        text_color=(15, 15, 15),
        alignment="left",
        offset_x=40.0,
        offset_y=40.0,
    )

    x0, y0, x1, y1 = separation.crop_bbox
    # The original spot should now be clean background, not still showing ink.
    original_patch = result.image_bgr[y0:y1, x0:x1]
    assert original_patch.std() < 5.0

    # The nudged-to spot (original + 40px in both directions) should have ink.
    nudged_patch = result.image_bgr[y0 + 40 : y1 + 40, x0 + 40 : x1 + 40]
    assert nudged_patch.std() > 5.0


def test_compose_region_handles_empty_crop_without_raising():
    image_bgr = np.zeros((10, 10, 3), dtype=np.uint8)
    alpha = np.zeros((0, 0), dtype=np.float32)
    background = BackgroundFill(kind="flat", color=(255, 255, 255))

    result = compose_region(
        image_bgr,
        (5, 5, 5, 5),
        alpha,
        background,
        "text",
        _find_font_path("Inter", 400),
        font_size=16.0,
        letter_spacing=0.0,
        baseline_local_y=0.0,
        text_color=(0, 0, 0),
        alignment="left",
    )

    assert result.image_bgr.shape == image_bgr.shape
