import numpy as np
from PIL import Image

from stages.detect import detect
from engines import PaddleEngine

path = "/fixtures/web_3x_dashboard.jpg"
image = Image.open(path).convert("RGB")
image_bgr = np.array(image)[:, :, ::-1].copy()

real = detect(image_bgr)
print("=== real stages.detect.detect() ===")
for line in real.lines:
    print(line.text, line.bbox, line.confidence, line.block_id)

print("\n=== PaddleEngine.run() (bench adapter) ===")
engine = PaddleEngine()
engine.construct()
result = engine.run(image_bgr)
for ln in result.lines:
    print(ln.text, ln.bbox, ln.confidence)
