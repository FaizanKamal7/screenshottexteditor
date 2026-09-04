import base64
import io
import json
import multiprocessing
import os
import time
import uuid
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass

import numpy as np
from fastapi import FastAPI, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from PIL import Image
from pydantic import ValidationError

from fonts.registry import find_font_path
from models import AnalyzeResponse, Region, RenderEdit, RenderRegionResult, RenderResponse
from stages.detect import DetectedLine, detect, estimate_scale_factor
from stages.match import detect_ui_element, estimate_color, estimate_layout, match_font
from stages.render_stage import compose_region
from stages.separate import separate

app = FastAPI(title="screenshottexteditor pipeline")

PIPELINE_SHARED_SECRET = os.environ.get("PIPELINE_SHARED_SECRET", "")

# match_font is the dominant cost per line (11 font candidates x 2 restart
# searches x ~90 tiny renders/scores each) and every line is independent of
# every other, so lines are farmed out across processes rather than run in
# one sequential loop. Real multiprocessing (not threads) because the work
# is CPU-bound Skia rendering + numpy scoring — the GIL would serialize
# threads back down to ~one core's worth of throughput anyway.
#
# The pool is a lazily-created singleton (first request pays the spawn
# cost, every later one reuses the same warm workers — including the font
# files they lru_cache in stages/match.py's render_text) rather than one
# created eagerly at import time. That laziness matters beyond a
# micro-optimization: on a "spawn" platform (Windows, macOS — anywhere
# without fork()), a worker process resolves `_process_line` by reimporting
# this module, which would re-run any eager top-level pool creation and
# spawn its own pool recursively. Deferring creation into a function that
# only the request-handling process ever calls avoids that entirely.
# Capped at 16 rather than left uncapped: each worker is one Skia-rendering,
# numpy-scoring process running flat out, so beyond ~16 concurrent workers the
# OS scheduler and forkserver/IPC overhead start eating into throughput rather
# than adding to it. Override via PIPELINE_MAX_WORKERS for a specific host.
_WORKER_COUNT = max(1, min(os.cpu_count() or 4, 16))
_executor: ProcessPoolExecutor | None = None


def _mp_context() -> multiprocessing.context.BaseContext:
    """"forkserver" where available, else "spawn" — never the platform-default "fork".

    Uvicorn runs an asyncio event loop plus a thread pool, so the request
    handler that creates this pool is itself multi-threaded. Forking
    directly from a multi-threaded process risks a hung child (a lock some
    other thread held mid-fork never gets released in the copy). forkserver
    sidesteps that by forking new workers from a dedicated helper process
    that is kept single-threaded for exactly this reason.
    """
    try:
        return multiprocessing.get_context("forkserver")
    except ValueError:
        return multiprocessing.get_context("spawn")


def _get_executor() -> ProcessPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor(
            max_workers=int(os.environ.get("PIPELINE_MAX_WORKERS", _WORKER_COUNT)), mp_context=_mp_context()
        )
    return _executor


def require_shared_secret(x_pipeline_secret: str | None) -> None:
    if not PIPELINE_SHARED_SECRET or x_pipeline_secret != PIPELINE_SHARED_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@dataclass
class LineTimings:
    """CPU seconds one worker actually spent in each stage of one line's
    stage-2/stage-3 work — measured inside the worker process, so this is
    real per-stage cost regardless of how many workers ran concurrently
    (unlike wall-clock time from the parent, which only shows the phase's
    total span). main.py's `_run_analysis` sums these across every line to
    report where CPU time is actually going (see docs/pipeline-tuning.md).
    """

    separate_s: float
    match_s: float
    color_s: float
    ui_s: float


def _process_line(image_bgr: np.ndarray, line: DetectedLine, region_id: str) -> tuple[Region, np.ndarray, LineTimings]:
    """One detected line's full stage-2/stage-3 work: separate, match font, estimate color/UI.

    Runs inside a worker process (see `_executor` above) — must not touch
    any state that isn't passed in as an argument. `region_id` is generated
    by the caller (not here, as it used to be) and reused for the same
    line's "detected" stub, "region" stream message, and final `result`
    entry, so the frontend can match them up by id as progressively richer
    versions of the same region arrive.
    """
    t0 = time.perf_counter()
    separation = separate(image_bgr, line.bbox)
    t1 = time.perf_counter()

    region_h = line.bbox[3]
    crop_shape = separation.alpha.shape

    match = match_font(line.text, separation.alpha, crop_shape, region_h)
    t2 = time.perf_counter()
    color = estimate_color(image_bgr, separation.alpha, separation.crop_bbox, separation.bg_variance)
    t3 = time.perf_counter()
    ui_element = detect_ui_element(image_bgr, line.bbox)
    t4 = time.perf_counter()

    region = Region(
        id=region_id,
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
    timings = LineTimings(separate_s=t1 - t0, match_s=t2 - t1, color_s=t3 - t2, ui_s=t4 - t3)
    return region, separation.alpha, timings


def _log_analyze_timings(timings: dict) -> None:
    """One-line, greppable timing report per /analyze request (see the
    stage breakdown docstring on `_run_analysis`). Plain print rather than
    `logging` — this is ad-hoc measurement instrumentation, not a
    permanent log line, and print guarantees it lands in container stdout
    without depending on whatever logging config uvicorn/the deployment
    happens to have.
    """
    print(f"analyze_timings {json.dumps(timings)}", flush=True)


def _run_analysis(contents: bytes):
    """Generator driving /analyze's NDJSON stream.

    Three message types, in order, all additive on top of the previous
    contract (existing consumers that only handle "progress"/"result" keep
    working unchanged):

    1. One `{"type": "detected", ...}` line, emitted right after OCR
       detection finishes and before any per-line enrichment (separate/
       font-match/color/UI-detect) starts — carries every detected line's
       text/bbox/block_id/OCR-confidence as bare `Region`s (everything
       enrichment would fill in left at its default: no font, no color, no
       alpha mask). This is the frontend's first chance to show something
       real: the text existed and roughly where, well before the
       expensive part (font matching) has run even once.
    2. One `{"type": "progress", ...}` and one `{"type": "region", ...}`
       line per detected line, as each one's full enrichment finishes —
       `region` carries that line's complete `Region` (same id as its
       "detected" stub, so a client can replace-by-id) at whatever
       alignment/line_height default it has before block-level layout
       (below) corrects it.
    3. One final `{"type": "result", ...}` line, same shape `AnalyzeResponse`
       as returned in one shot — every region's alignment/line_height now
       block-corrected, the authoritative final state.

    Kept as a plain generator (not async) since every step here is
    CPU-bound, not I/O-bound.

    Lines are submitted to `_executor` up front and streamed back via
    `as_completed`, so `current` counts completions rather than a fixed
    processing order — with several workers running at once, a later line
    can easily finish before an earlier one. The final `regions`/`masks`
    lists are still reassembled in original detection order (line order
    matters for display and for `estimate_scale_factor`'s consumers, even
    though completion order doesn't).

    Stage timings are collected throughout and printed once at the end via
    `_log_analyze_timings` — this is deliberately not part of the response
    schema (keeps the wire contract narrowly scoped to what the frontend
    actually consumes); it's meant to be read from container/test logs
    while deciding where the next real optimization should go.
    """
    request_start = time.perf_counter()

    image = Image.open(io.BytesIO(contents)).convert("RGB")
    width, height = image.size
    image_bgr = np.array(image)[:, :, ::-1].copy()

    detect_result = detect(image_bgr)
    detect_done = time.perf_counter()
    lines = detect_result.lines
    total = len(lines)

    # Stable per-line ids, generated once here rather than inside
    # _process_line as before: the same id has to appear on this line's
    # "detected" stub below, its later "region" message, and the final
    # "result" entry for a client to recognize them as the same region.
    region_ids = [str(uuid.uuid4()) for _ in lines]

    detected_regions = [
        Region(id=region_ids[i], text=line.text, bbox=line.bbox, block_id=line.block_id, confidence=line.confidence)
        for i, line in enumerate(lines)
    ]
    time_to_detected_s = time.perf_counter() - request_start
    yield json.dumps({"type": "detected", "total": total, "regions": [r.model_dump() for r in detected_regions]}) + "\n"
    yield json.dumps({"type": "progress", "current": 0, "total": total}) + "\n"

    regions: list[Region | None] = [None] * total
    masks: list[np.ndarray | None] = [None] * total

    executor = _get_executor()
    futures = {
        executor.submit(_process_line, image_bgr, line, region_ids[i]): i for i, line in enumerate(lines)
    }

    enrich_start = time.perf_counter()
    separate_s_total = 0.0
    match_s_total = 0.0
    color_s_total = 0.0
    ui_s_total = 0.0

    completed = 0
    for future in as_completed(futures):
        index = futures[future]
        region, mask, timings = future.result()
        regions[index] = region
        masks[index] = mask
        separate_s_total += timings.separate_s
        match_s_total += timings.match_s
        color_s_total += timings.color_s
        ui_s_total += timings.ui_s
        completed += 1
        yield json.dumps({"type": "progress", "current": completed, "total": total}) + "\n"
        yield json.dumps({"type": "region", "current": completed, "total": total, "region": region.model_dump()}) + "\n"

    enrich_done = time.perf_counter()

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

    total_request_s = time.perf_counter() - request_start
    _log_analyze_timings(
        {
            "region_count": total,
            "engine_init_s": round(detect_result.engine_init_s, 4),
            "ocr_run_s": round(detect_result.ocr_run_s, 4),
            "detect_wall_s": round(detect_done - request_start, 4),
            "time_to_detected_s": round(time_to_detected_s, 4),
            "separation_cpu_s": round(separate_s_total, 4),
            "font_matching_cpu_s": round(match_s_total, 4),
            "enrichment_cpu_s": round(color_s_total + ui_s_total, 4),
            "enrich_phase_wall_s": round(enrich_done - enrich_start, 4),
            "time_to_full_result_s": round(total_request_s, 4),
            "total_request_s": round(total_request_s, 4),
        }
    )

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
