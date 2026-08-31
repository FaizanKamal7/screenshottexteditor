import numpy as np
from PIL import Image, ImageDraw, ImageFont

from stages.separate import separate


def _render_text_image(text: str, size: tuple[int, int] = (220, 60)) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    image = Image.new("RGB", size, color=(250, 250, 250))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    text_pos = (12, 18)
    draw.text(text_pos, text, fill=(20, 20, 20), font=font)

    bbox_pixels = draw.textbbox(text_pos, text, font=font)
    bbox = (
        float(bbox_pixels[0] - 2),
        float(bbox_pixels[1] - 2),
        float(bbox_pixels[2] - bbox_pixels[0] + 4),
        float(bbox_pixels[3] - bbox_pixels[1] + 4),
    )

    image_bgr = np.array(image)[:, :, ::-1].copy()
    return image_bgr, bbox


def test_flat_background_produces_alpha_mask_covering_text():
    image_bgr, bbox = _render_text_image("Hello")

    result = separate(image_bgr, bbox)

    assert result.bg_variance < 15.0
    assert result.alpha.max() > 0.5
    assert result.alpha_mask_png != ""


def test_char_boxes_roughly_match_character_count():
    image_bgr, bbox = _render_text_image("Hi")

    result = separate(image_bgr, bbox)

    assert 1 <= len(result.char_boxes) <= 4


def test_textured_background_is_detected_as_non_flat():
    rng = np.random.default_rng(seed=42)
    noisy = rng.integers(0, 255, size=(60, 220, 3), dtype=np.uint8)
    image = Image.fromarray(noisy[:, :, ::-1], mode="RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((12, 18), "Hi", fill=(0, 0, 0), font=font)

    image_bgr = np.array(image)[:, :, ::-1].copy()
    bbox = (10.0, 16.0, 40.0, 24.0)

    result = separate(image_bgr, bbox)

    assert result.bg_variance >= 15.0
    assert result.alpha.shape[0] > 0 and result.alpha.shape[1] > 0
