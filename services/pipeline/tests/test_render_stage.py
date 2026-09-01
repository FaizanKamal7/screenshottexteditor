import numpy as np
from PIL import Image, ImageDraw, ImageFont

from fonts.registry import FONT_REGISTRY
from models import BackgroundFill
from stages.render_stage import compose_region, fit_font_size
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
