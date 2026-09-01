import base64
import io
import json
import os
import uuid
from collections import defaultdict

import numpy as np
from fastapi import FastAPI, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from PIL import Image
from pydantic import ValidationError

from fonts.registry import find_font_path
from models import AnalyzeResponse, Region, RenderEdit, RenderRegionResult, RenderResponse
from stages.detect import detect, estimate_scale_factor
from stages.match import detect_ui_element, estimate_color, estimate_layout, match_font
from stages.render_stage import compose_region
from stages.separate import separate

app = FastAPI(title="screenshottexteditor pipeline")

PIPELINE_SHARED_SECRET = os.environ.get("PIPELINE_SHARED_SECRET", "")


def require_shared_secret(x_pipeline_secret: str | None) -> None:
    if not PIPELINE_SHARED_SECRET or x_pipeline_secret != PIPELINE_SHARED_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _run_analysis(contents: bytes):
    """Generator driving /analyze's NDJSON stream.

    Yields a `{"type": "progress", ...}` line after each detected line is
    processed (the only per-item work the client can't otherwise observe),
    then a final `{"type": "result", ...}` line carrying the same shape
    `AnalyzeResponse` used to return in one shot. Kept as a plain generator
    (not async) since every step here is CPU-bound, not I/O-bound.
    """
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    width, height = image.size
    image_bgr = np.array(image)[:, :, ::-1].copy()

    detect_result = detect(image_bgr)
    total = len(detect_result.lines)
    yield json.dumps({"type": "progress", "current": 0, "total": total}) + "\n"

    regions: list[Region] = []
    masks: list[np.ndarray] = []
    for index, line in enumerate(detect_result.lines):
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
                # The render-match score alone can be confidently wrong when
                # OCR misread the text itself (e.g. a spurious trailing
                # period) — a font can still render that wrong text as a
                # decent shape match. Taking the min with OCR's own
                # recognition confidence surfaces that case as low-confidence
                # instead of silently passing it through.
                confidence=min(line.confidence, match.score),
                alpha_mask_png=separation.alpha_mask_png,
                font_family=match.family,
                font_weight=match.weight,
                font_size=match.size,
                letter_spacing=match.letter_spacing,
                baseline_y=separation.crop_bbox[1] + match.baseline_y,
                x_offset=separation.crop_bbox[0] + match.x_offset,
                text_color=color.text_color,
                background=color.background,
                ui_element=ui_element,
                font_candidates=match.top_candidates,
            )
        )
        yield json.dumps({"type": "progress", "current": index + 1, "total": total}) + "\n"

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

    response = AnalyzeResponse(image_width=width, image_height=height, scale_factor=scale_factor, regions=regions)
    yield json.dumps({"type": "result", **response.model_dump()}) + "\n"


@app.post("/analyze")
async def analyze(
    file: UploadFile,
    x_pipeline_secret: str | None = Header(default=None, alias="X-Pipeline-Secret"),
) -> StreamingResponse:
    require_shared_secret(x_pipeline_secret)

    contents = await file.read()
    return StreamingResponse(_run_analysis(contents), media_type="application/x-ndjson")


@app.post("/render", response_model=RenderResponse)
async def render(
    file: UploadFile,
    edits: str = Form(...),
    x_pipeline_secret: str | None = Header(default=None, alias="X-Pipeline-Secret"),
) -> RenderResponse:
    require_shared_secret(x_pipeline_secret)

    try:
        edit_list = [RenderEdit(**item) for item in json.loads(edits)]
    except (json.JSONDecodeError, TypeError, ValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid edits payload: {exc}") from exc

    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    image_bgr = np.array(image)[:, :, ::-1].copy()

    results: list[RenderRegionResult] = []
    for edit in edit_list:
        try:
            font_path = find_font_path(edit.font_family, edit.font_weight)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        separation = separate(image_bgr, edit.bbox)
        local_baseline = edit.baseline_y - separation.crop_bbox[1]
        local_x_offset = edit.x_offset - separation.crop_bbox[0]

        compose_result = compose_region(
            image_bgr,
            separation.crop_bbox,
            separation.alpha,
            edit.background,
            edit.text,
            font_path,
            edit.font_size,
            edit.letter_spacing,
            local_baseline,
            edit.text_color,
            edit.alignment,
            local_x_offset,
            edit.offset_x,
            edit.offset_y,
        )
        image_bgr = compose_result.image_bgr
        results.append(
            RenderRegionResult(region_id=edit.region_id, font_size=compose_result.font_size, overflowed=compose_result.overflowed)
        )

    out_image = Image.fromarray(image_bgr[:, :, ::-1])
    buffer = io.BytesIO()
    out_image.save(buffer, format="PNG")
    image_png_base64 = base64.b64encode(buffer.getvalue()).decode("ascii")

    return RenderResponse(image_png_base64=image_png_base64, results=results)
