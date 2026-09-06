import sys

sys.path.insert(0, "/app/tests")
import numpy as np
from PIL import Image

from fonts.registry import find_font_path
from stages.match import estimate_color, match_font
from stages.render_stage import compose_region
from stages.separate import separate
from test_round_trip import _round_trip_region

path = "/fixtures/web_3x_dashboard.jpg"
image = Image.open(path).convert("RGB")
image_bgr = np.array(image)[:, :, ::-1].copy()

bbox = (36.0, 30.0, 107.0, 29.0)
text = "Revenue"
conf = 0.9989538192749023

print("=== real _round_trip_region ===")
print(_round_trip_region(image_bgr, bbox, text, conf))

print("=== my inline copy ===")
separation = separate(image_bgr, bbox)
match = match_font(text, separation.alpha, separation.alpha.shape, bbox[3])
color = estimate_color(image_bgr, separation.alpha, separation.crop_bbox, separation.bg_variance)
font_path = find_font_path(match.family, match.weight)
result = compose_region(
    image_bgr, separation.crop_bbox, separation.alpha, color.background, text, font_path,
    match.size, match.letter_spacing, match.baseline_y, color.text_color,
    alignment="left", base_x_offset=match.x_offset,
)
x0, y0, x1, y1 = separation.crop_bbox
original_patch = image_bgr[y0:y1, x0:x1].astype(np.float64)
rendered_patch = result.image_bgr[y0:y1, x0:x1].astype(np.float64)
mean_delta = float(np.abs(original_patch - rendered_patch).mean())
print(mean_delta, min(conf, match.score))
print("match:", match)
