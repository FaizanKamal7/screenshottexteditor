from functools import lru_cache

import numpy as np
import skia


@lru_cache(maxsize=32)
def _load_typeface(font_path: str) -> skia.Typeface:
    typeface = skia.Typeface.MakeFromFile(font_path)
    if typeface is None:
        raise ValueError(f"could not load font at {font_path}")
    return typeface


def render_text(
    text: str,
    font_path: str,
    size_px: float,
    letter_spacing_px: float,
    origin_xy: tuple[float, float],
    canvas_size: tuple[int, int],
) -> np.ndarray:
    """Render `text` into an alpha-only buffer of shape (height, width).

    `origin_xy` is (x, baseline_y): x is the left edge to start drawing
    from, baseline_y is the absolute y of the text baseline within the
    canvas. Returns float32 alpha in 0..1, matching stages/separate.py's
    alpha mask convention so the two can be compared directly.
    """
    width, height = canvas_size
    if width <= 0 or height <= 0 or not text:
        return np.zeros((max(height, 1), max(width, 1)), dtype=np.float32)

    typeface = _load_typeface(font_path)
    font = skia.Font(typeface, size_px)
    paint = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)

    glyphs = font.textToGlyphs(text)
    widths = font.getWidths(glyphs)

    x_offset, baseline_y = origin_xy
    x_positions: list[float] = []
    cursor = x_offset
    for advance in widths:
        x_positions.append(cursor)
        cursor += advance + letter_spacing_px

    blob = skia.TextBlob.MakeFromPosTextH(text.encode("utf-8"), x_positions, baseline_y, font)

    surface = skia.Surface.MakeRaster(skia.ImageInfo.MakeA8(width, height))
    with surface as canvas:
        canvas.clear(0)
        if blob is not None:
            canvas.drawTextBlob(blob, 0, 0, paint)

    image = surface.makeImageSnapshot()
    array = image.toarray()  # HxW, uint8, alpha coverage
    alpha = array.astype(np.float32) / 255.0
    return alpha


def measure_text_width(text: str, font_path: str, size_px: float, letter_spacing_px: float) -> float:
    """Advance width of `text` at `size_px`, matching render_text's glyph positioning."""
    if not text:
        return 0.0
    typeface = _load_typeface(font_path)
    font = skia.Font(typeface, size_px)
    glyphs = font.textToGlyphs(text)
    if len(glyphs) == 0:
        return 0.0
    widths = font.getWidths(glyphs)
    return float(sum(widths) + letter_spacing_px * (len(widths) - 1))
