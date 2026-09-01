import numpy as np

from models import BackgroundFill, GradientStop
from stages.erase import erase, fill_array


def test_fill_array_flat_matches_requested_color():
    fill = fill_array(BackgroundFill(kind="flat", color=(10, 20, 30)), height=4, width=4)

    assert fill.shape == (4, 4, 3)
    assert np.allclose(fill[0, 0], [30, 20, 10])  # BGR


def test_fill_array_gradient_interpolates_between_stops():
    background = BackgroundFill(
        kind="gradient",
        angle_deg=0.0,
        stops=[GradientStop(position=0.0, color=(0, 0, 0)), GradientStop(position=1.0, color=(255, 255, 255))],
    )

    fill = fill_array(background, height=1, width=10)

    assert np.allclose(fill[0, 0], [0, 0, 0], atol=1.0)
    assert np.allclose(fill[0, -1], [255, 255, 255], atol=1.0)
    assert fill[0, 5, 0] > fill[0, 0, 0]


def test_erase_replaces_fully_opaque_region_with_background_color():
    image = np.full((20, 20, 3), 200, dtype=np.uint8)  # light gray everywhere
    alpha = np.ones((10, 10), dtype=np.float32)  # fully "text" inside the crop
    crop_bbox = (5, 5, 15, 15)
    background = BackgroundFill(kind="flat", color=(200, 200, 200))

    result = erase(image, crop_bbox, alpha, background)

    assert np.allclose(result[5:15, 5:15], 200, atol=1)
    assert np.array_equal(result[0:5, 0:5], image[0:5, 0:5])  # untouched outside the crop


def test_erase_leaves_background_pixels_unchanged_where_alpha_is_zero():
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    image[:, :] = (50, 60, 70)
    alpha = np.zeros((10, 10), dtype=np.float32)
    crop_bbox = (0, 0, 10, 10)
    background = BackgroundFill(kind="flat", color=(255, 255, 255))

    result = erase(image, crop_bbox, alpha, background)

    assert np.array_equal(result, image)
