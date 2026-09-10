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


def test_erase_leaves_no_ghost_at_partially_anti_aliased_edges():
    """The anti-aliased fringe around a solid glyph core must fully
    disappear too, not just the fully-opaque interior — regression coverage
    for the old pure-linear-blend behavior, which left a visible ghost at
    partial-alpha edge pixels (e.g. a 40%-alpha pixel stayed 40% of the way
    toward the old glyph color).
    """
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    image[:, :] = (10, 20, 30)  # real background, visible in a ring around the glyph
    image[4:12, 4:12] = (255, 255, 255)  # old solid white glyph fill
    crop_bbox = (0, 0, 16, 16)

    alpha = np.zeros((16, 16), dtype=np.float32)
    alpha[4:12, 4:12] = 1.0
    # Anti-aliased fringe one ring out from the solid core.
    alpha[3, 4:12] = alpha[12, 4:12] = alpha[4:12, 3] = alpha[4:12, 12] = 0.4

    background = BackgroundFill(kind="flat", color=(30, 20, 10))  # deliberately not the real bg color
    result = erase(image, crop_bbox, alpha, background)

    assert np.all(result[4:12, 4:12] < 250)
    assert np.all(result[3, 4:12] < 250)


def test_erase_reconstructs_from_real_neighboring_pixels_not_a_rectangle_fill():
    """Background reconstruction must come from the real surrounding pixels
    (mask-driven inpainting), not a flat/gradient guess painted over the
    whole crop rectangle — and pixels outside the glyph mask, even ones
    close to it, must stay pixel-exact untouched.
    """
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    image[:, :] = (10, 20, 30)
    image[4:12, 4:12] = (255, 255, 255)
    crop_bbox = (0, 0, 16, 16)

    alpha = np.zeros((16, 16), dtype=np.float32)
    alpha[4:12, 4:12] = 1.0
    alpha[3, 4:12] = alpha[12, 4:12] = alpha[4:12, 3] = alpha[4:12, 12] = 0.4

    background = BackgroundFill(kind="flat", color=(30, 20, 10))
    result = erase(image, crop_bbox, alpha, background)

    # Real background well outside the mask is untouched, not washed over.
    assert np.array_equal(result[0:2, :], image[0:2, :])
    assert np.array_equal(result[:, 0:2], image[:, 0:2])

    # Reconstructed interior matches the real surrounding background color,
    # not the (deliberately different) fitted flat/gradient guess.
    assert np.allclose(result[7, 7].astype(np.float64), [10, 20, 30], atol=30)


def test_erase_falls_back_to_fill_when_mask_covers_the_whole_crop():
    """When glyphs fill the entire assigned crop, there's no real background
    pixel left anywhere in it for inpainting to source texture from — that
    edge case still uses the fitted flat/gradient guess, same as before.
    """
    image = np.full((10, 10, 3), 200, dtype=np.uint8)
    alpha = np.ones((10, 10), dtype=np.float32)
    crop_bbox = (0, 0, 10, 10)
    background = BackgroundFill(kind="flat", color=(1, 2, 3))

    result = erase(image, crop_bbox, alpha, background)

    assert np.allclose(result, [3, 2, 1], atol=1)  # BGR
