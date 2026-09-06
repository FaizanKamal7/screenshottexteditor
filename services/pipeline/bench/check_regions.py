import sys

import numpy as np
from PIL import Image

from stages.detect import detect

path = sys.argv[1]
image = Image.open(path).convert("RGB")
image_bgr = np.array(image)[:, :, ::-1].copy()

result = detect(image_bgr)
print(f"region_count={len(result.lines)} engine_init_s={result.engine_init_s:.3f} ocr_run_s={result.ocr_run_s:.3f}")
for line in result.lines:
    print(f"  bbox={tuple(round(v,1) for v in line.bbox)} conf={line.confidence:.3f} text={line.text!r}")
