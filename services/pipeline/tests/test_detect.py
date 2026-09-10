import numpy as np
from PIL import Image, ImageDraw, ImageFont

from stages.detect import detect, estimate_scale_factor, group_into_blocks, neighbor_clamp_for


def _render_screenshot_like_image() -> np.ndarray:
    image = Image.new("RGB", (400, 300), color=(250, 250, 250))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=32)

    draw.text((20, 20), "Account Settings", fill=(20, 20, 20), font=font)
    draw.text((20, 60), "Manage your profile", fill=(80, 80, 80), font=font)
    draw.text((20, 220), "Continue", fill=(20, 20, 20), font=font)

    return np.array(image)[:, :, ::-1].copy()


def test_detect_finds_at_least_one_line_with_valid_bbox():
    image_bgr = _render_screenshot_like_image()

    result = detect(image_bgr)

    assert len(result.lines) >= 1
    for line in result.lines:
        _, _, w, h = line.bbox
        assert w > 0
        assert h > 0
        assert line.text != ""


def test_group_into_blocks_keeps_close_aligned_lines_together():
    boxed_lines = [
        {"text": "Account Settings", "bbox": (20.0, 20.0, 180.0, 30.0), "confidence": 0.99},
        {"text": "Manage your profile", "bbox": (20.0, 60.0, 200.0, 30.0), "confidence": 0.98},
    ]

    lines = group_into_blocks(boxed_lines)

    assert len({line.block_id for line in lines}) == 1


def test_group_into_blocks_splits_on_large_vertical_gap():
    boxed_lines = [
        {"text": "Account Settings", "bbox": (20.0, 20.0, 180.0, 30.0), "confidence": 0.99},
        {"text": "Manage your profile", "bbox": (20.0, 60.0, 200.0, 30.0), "confidence": 0.98},
        {"text": "Continue", "bbox": (20.0, 220.0, 100.0, 30.0), "confidence": 0.97},
    ]

    lines = group_into_blocks(boxed_lines)

    assert len({line.block_id for line in lines}) == 2


def test_group_into_blocks_splits_on_left_edge_shift():
    boxed_lines = [
        {"text": "Label", "bbox": (20.0, 20.0, 80.0, 20.0), "confidence": 0.99},
        {"text": "Indented value", "bbox": (60.0, 44.0, 120.0, 20.0), "confidence": 0.98},
    ]

    lines = group_into_blocks(boxed_lines)

    assert len({line.block_id for line in lines}) == 2


def test_estimate_scale_factor_defaults_to_1x_for_empty_masks():
    assert estimate_scale_factor([]) == 1


def test_estimate_scale_factor_returns_valid_bucket_for_synthetic_mask():
    mask = np.zeros((40, 40), dtype=np.float32)
    mask[10:30, 10:14] = 1.0  # a ~4px-wide vertical stroke

    scale = estimate_scale_factor([mask])

    assert scale in (1, 2, 3)


def test_neighbor_clamp_for_bounds_tight_vertically_stacked_lines():
    """Regression coverage for a receipt-style 'Order Number:' / 'Date:'
    pair: two lines close enough together that CROP_PADDING_PX plus normal
    OCR bbox slop would otherwise bridge the gap between them.
    """
    order_bbox = (20.0, 10.0, 180.0, 12.0)  # y: 10-22
    date_bbox = (20.0, 24.0, 140.0, 14.0)  # y: 24-38, only 2px below order_bbox

    min_x, max_x, min_y, max_y = neighbor_clamp_for(date_bbox, [order_bbox, date_bbox])

    assert min_y == 23.0  # midpoint of the 22-24 gap between the two reported boxes
    assert max_y == float("inf")  # nothing below date_bbox to clamp against
    assert min_x == 0.0 and max_x == float("inf")  # order_bbox overlaps horizontally, not a side-by-side neighbor


def test_neighbor_clamp_for_bounds_side_by_side_labels():
    left_bbox = (10.0, 10.0, 40.0, 20.0)  # x: 10-50
    right_bbox = (54.0, 10.0, 40.0, 20.0)  # x: 54-94, only 4px to the right

    min_x, max_x, min_y, max_y = neighbor_clamp_for(left_bbox, [right_bbox])

    assert max_x == 52.0  # midpoint of the 50-54 gap
    assert min_x == 0.0
    assert min_y == 0.0 and max_y == float("inf")


def test_neighbor_clamp_for_ignores_diagonal_boxes():
    """A box that overlaps neither axis (diagonally offset) isn't a real
    visual neighbor -- e.g. two unrelated fields in different rows AND
    columns -- and must not affect the clamp at all.
    """
    bbox = (20.0, 20.0, 40.0, 20.0)
    diagonal = (200.0, 200.0, 40.0, 20.0)  # overlaps neither axis

    bounds = neighbor_clamp_for(bbox, [diagonal])

    assert bounds == (0.0, float("inf"), 0.0, float("inf"))


def test_neighbor_clamp_for_still_bounds_a_distant_aligned_neighbor():
    """A far-away neighbor in the same column still produces a (very loose)
    clamp -- there's no distance cutoff, just whichever neighbor is closest
    on that axis. Harmless in practice since normal padding never reaches
    anywhere near that far.
    """
    bbox = (20.0, 20.0, 40.0, 20.0)
    far_below = (20.0, 500.0, 40.0, 20.0)  # same columns, y: 500-520

    _, _, _, max_y = neighbor_clamp_for(bbox, [far_below])

    assert max_y == 270.0  # midpoint of the 40-500 gap


def test_neighbor_clamp_for_ignores_itself_when_present_in_other_bboxes():
    bbox = (20.0, 20.0, 40.0, 20.0)

    bounds = neighbor_clamp_for(bbox, [bbox])

    assert bounds == (0.0, float("inf"), 0.0, float("inf"))
