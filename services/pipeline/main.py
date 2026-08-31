import io
import os
import uuid
from collections import defaultdict

import numpy as np
from fastapi import FastAPI, Header, HTTPException, UploadFile, status
from PIL import Image

from models import AnalyzeResponse, Region
from stages.detect import detect, estimate_scale_factor
from stages.match import detect_ui_element, estimate_color, estimate_layout, match_font
from stages.separate import separate

app = FastAPI(title="screenshottexteditor pipeline")

PIPELINE_SHARED_SECRET = os.environ.get("PIPELINE_SHARED_SECRET", "")


def require_shared_secret(x_pipeline_secret: str | None) -> None:
    if not PIPELINE_SHARED_SECRET or x_pipeline_secret != PIPELINE_SHARED_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile,
    x_pipeline_secret: str | None = Header(default=None, alias="X-Pipeline-Secret"),
) -> AnalyzeResponse:
    require_shared_secret(x_pipeline_secret)

    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    width, height = image.size
    image_bgr = np.array(image)[:, :, ::-1].copy()

    detect_result = detect(image_bgr)

    regions: list[Region] = []
    masks: list[np.ndarray] = []
    for line in detect_result.lines:
        separation = separate(image_bgr, line.bbox)
        masks.append(separation.alpha)

        region_h = line.bbox[3]
        crop_shape = separation.alpha.shape

        match = match_font(line.text, separation.alpha, crop_shape, region_h)
        color = estimate_color(image_bgr, separation.alpha, separation.crop_bbox, separation.bg_variance)
        ui_element = detect_ui_element(image_bgr, line.bbox)

        regions.append(
            Region(
                id=str(uuid.uuid4()),
                text=line.text,
                bbox=line.bbox,
                block_id=line.block_id,
                chars=separation.char_boxes,
                confidence=match.score,
                alpha_mask_png=separation.alpha_mask_png,
                font_family=match.family,
                font_weight=match.weight,
                font_size=match.size,
                letter_spacing=match.letter_spacing,
                baseline_y=separation.crop_bbox[1] + match.baseline_y,
                text_color=color.text_color,
                background=color.background,
                ui_element=ui_element,
                font_candidates=match.top_candidates,
            )
        )

    blocks: dict[str, list[int]] = defaultdict(list)
    for index, region in enumerate(regions):
        blocks[region.block_id].append(index)

    for indices in blocks.values():
        block_bboxes = [regions[i].bbox for i in indices]
        layout = estimate_layout(block_bboxes)
        for i in indices:
            regions[i].alignment = layout.alignment
            regions[i].line_height = layout.line_height

    scale_factor = estimate_scale_factor(masks)

    return AnalyzeResponse(image_width=width, image_height=height, scale_factor=scale_factor, regions=regions)
