import numpy as np
from PIL import Image, ImageDraw, ImageFont

from stages.detect import detect, estimate_scale_factor, group_into_blocks


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
