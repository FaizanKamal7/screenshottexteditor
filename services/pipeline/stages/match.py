from dataclasses import dataclass

import cv2
import numpy as np

from fonts.registry import FONT_REGISTRY
from models import BackgroundFill, FontCandidateScore, GradientStop, UiElement
from renderer import render_text

IOU_WEIGHT = 0.7
SSIM_WEIGHT = 0.3

# Parameters _fast_ssim hardcodes to exactly match what score_alpha's SSIM
# call used to resolve to when it went through skimage's
# `structural_similarity(rendered, target, data_range=1.0)` directly, under
# skimage 0.26's defaults (verified against its installed source, not
# assumed): win_size=7 ("backwards compatibility" default when
# gaussian_weights=False, which is itself the default), K1=0.01/K2=0.03
# (skimage's own defaults), use_sample_covariance=True (skimage's own
# default) i.e. cov_norm = NP/(NP-1). Not meant as general SSIM parameters —
# this is a drop-in replacement for this one call site, not a library.
SSIM_WIN_SIZE = 7
SSIM_K1 = 0.01
SSIM_K2 = 0.03

SIZE_GRID_STEPS = 7
SIZE_SEARCH_MIN_RATIO = 0.55
SIZE_SEARCH_MAX_RATIO = 1.35

LETTER_SPACING_SEARCH_PX = 2.0

# Real ink rarely starts exactly at the crop's left edge (CROP_PADDING_PX plus
# normal glyph left-bearing), but every candidate used to be scored rendered
# flush at x=0 regardless — a constant few-px horizontal miss that hurts IoU
# for every candidate roughly equally, on text whose stroke widths are often
# themselves only 1-3px. X_OFFSET_SEARCH_PX is a starting guess at how far
# that miss can reasonably be, not a measured bound — see docs/pipeline-tuning.md.
X_OFFSET_SEARCH_PX = 8.0
X_OFFSET_GRID_STEPS = 7

# The coarse->refine search below is coordinate descent (size, then
# letter-spacing, then x-offset, one more size pass), which can converge to a
# worse local optimum for some candidates than others — enough to let a
# wrong font/weight "win" even when the right one would score better if its
# own search had converged properly (confirmed: a regular-weight source
# matched as bold, scoring 0.45 against a true reachable ~0.68). Running each
# candidate's search from a second starting point (different initial
# baseline guess and a half-step-shifted size grid) and keeping whichever
# converges higher roughly doubles stage-3 render cost per region but
# meaningfully reduces how often a candidate gets stuck. (baseline_ratio,
# size_grid_phase) pairs — see _search_candidate.
RESTART_CONFIGS: list[tuple[float, float]] = [
    (0.8, 0.0),
    (0.72, 0.5),
]

FLAT_BACKGROUND_VARIANCE_THRESHOLD = 15.0  # kept in sync with stages/separate.py

UI_ELEMENT_PADDING_PX = 10
UI_ELEMENT_FAR_PADDING_PX = 30
UI_ELEMENT_VARIANCE_THRESHOLD = 20.0
UI_ELEMENT_COLOR_DELTA_THRESHOLD = 25.0
FLOOD_FILL_TOLERANCE = 18


@dataclass
class MatchResult:
    family: str
    weight: int
    size: float
    letter_spacing: float
    baseline_y: float
    x_offset: float
    score: float
    top_candidates: list[FontCandidateScore]


@dataclass
class ColorResult:
    text_color: tuple[int, int, int]
    background: BackgroundFill


@dataclass
class LayoutInfo:
    alignment: str
    line_height: float | None


def iou(binary_a: np.ndarray, binary_b: np.ndarray) -> float:
    intersection = np.logical_and(binary_a, binary_b).sum()
    union = np.logical_or(binary_a, binary_b).sum()
    if union == 0:
        return 1.0
    return float(intersection) / float(union)


def _box_filter(a: np.ndarray) -> np.ndarray:
    """size=7 windowed mean, same math as `scipy.ndimage.uniform_filter(a, size=7)`.

    Uses `cv2.boxFilter` instead of scipy's `uniform_filter`: same separable
    box-mean computation, but ~2x faster on the array sizes this is actually
    called on (real captured region crops, benchmarked in
    docs/pipeline-tuning.md). Border/padding mode is irrelevant to the
    result despite scipy and cv2 defaulting to different edge-extension
    conventions ('reflect' vs BORDER_REFLECT_101): `_fast_ssim` always crops
    `pad = (win_size-1)//2 = 3` rows/cols off each edge of the final SSIM
    map before averaging, and a size-7 filter's output at index i only
    touches out-of-bounds (border-extended) input when i is within 3 of an
    edge — exactly the region the crop discards. Verified empirically too,
    not just reasoned: BORDER_REFLECT and BORDER_REFLECT_101 produced
    bit-identical `_fast_ssim` output in testing.
    """
    return cv2.boxFilter(a, ddepth=-1, ksize=(SSIM_WIN_SIZE, SSIM_WIN_SIZE))


def _fast_ssim(im1: np.ndarray, im2: np.ndarray, data_range: float = 1.0) -> float:
    """Drop-in replacement for `structural_similarity(im1, im2, data_range=1.0)`
    as score_alpha actually calls it — same formula (Wang et al. 2004, same
    as skimage 0.26's `structural_similarity` source), same size-7 windowed
    stats (see `_box_filter`), same K1/K2/cov_norm constants, same final
    float64 mean over the 3px-cropped SSIM map.

    Verified bit-exact against skimage's structural_similarity across 34,369
    real (rendered, target) pairs captured from actual match_font() runs on
    every region in every tests/fixtures image when this used
    `scipy.ndimage.uniform_filter` (max abs diff: 0.0, not just "close") —
    see docs/pipeline-tuning.md. Swapping in `cv2.boxFilter` (see
    `_box_filter`) is not bit-exact against that scipy baseline (float-noise
    level differences, ~1e-8, from a different summation order) but was
    re-verified end-to-end against all 34 real regions: identical winning
    family/weight in every region, score/geometry differences ~1e-8-1e-9 —
    far below any threshold (`xatol`) that governs a search decision.
    ~1.39x full match_font wall-clock speedup measured on the same 34
    regions.
    """
    if np.any(np.array(im1.shape) < SSIM_WIN_SIZE):
        # Matches structural_similarity's own guard (raised as ValueError
        # for the same reason: a win_size=7 window can't be centered
        # anywhere in a dimension shorter than 7px) rather than silently
        # returning a number skimage would have refused to compute.
        raise ValueError(
            "win_size exceeds image extent — image must be at least "
            f"{SSIM_WIN_SIZE}x{SSIM_WIN_SIZE}, got shape {im1.shape}"
        )

    float_type = im1.dtype if im1.dtype in (np.float32, np.float64) else np.float64
    im1 = im1.astype(float_type, copy=False)
    im2 = im2.astype(float_type, copy=False)

    win_size = SSIM_WIN_SIZE
    NP = win_size**2
    cov_norm = NP / (NP - 1)  # use_sample_covariance=True, skimage's default

    ux = _box_filter(im1)
    uy = _box_filter(im2)
    uxx = _box_filter(im1 * im1)
    uyy = _box_filter(im2 * im2)
    uxy = _box_filter(im1 * im2)

    vx = cov_norm * (uxx - ux * ux)
    vy = cov_norm * (uyy - uy * uy)
    vxy = cov_norm * (uxy - ux * uy)

    R = data_range
    C1 = (SSIM_K1 * R) ** 2
    C2 = (SSIM_K2 * R) ** 2

    A1 = 2 * ux * uy + C1
    A2 = 2 * vxy + C2
    B1 = ux**2 + uy**2 + C1
    B2 = vx + vy + C2
    D = B1 * B2
    S = (A1 * A2) / D

    pad = (win_size - 1) // 2
    return float(S[pad:-pad, pad:-pad].mean(dtype=np.float64))


def score_alpha(rendered: np.ndarray, target: np.ndarray) -> float:
    if rendered.shape != target.shape:
        raise ValueError("rendered and target alpha must share the same shape")
    binary_rendered = rendered > 0.5
    binary_target = target > 0.5
    iou_score = iou(binary_rendered, binary_target)

    if rendered.size < 49:  # skimage's win_size (7) needs >=7px per side
        ssim_score = iou_score
    else:
        # _fast_ssim, not skimage's structural_similarity: verified
        # bit-exact against it (see _fast_ssim's docstring) but skips its
        # generic dispatch/validation overhead.
        ssim_score = _fast_ssim(rendered, target, data_range=1.0)

    return IOU_WEIGHT * iou_score + SSIM_WEIGHT * ssim_score


def _search_candidate(
    text: str,
    font_path: str,
    canvas_size: tuple[int, int],
    region_h: float,
    target_alpha: np.ndarray,
    default_baseline_ratio: float,
    size_grid_phase: float,
) -> tuple[float, float, float, float, float]:
    """One full coarse-grid -> golden-section-refine search for one font file, from one starting point.

    Baseline is fit once per phase (not on every golden-section evaluation):
    refitting it inside every objective call would multiply the render count
    by the baseline search width and also make the objective noisier than
    golden-section's unimodality assumption tolerates.

    Some of the (size, letter_spacing, x_offset, baseline_y) tuples evaluated
    below recur exactly — e.g. step 7's converged size can land on a point
    step 3 already tried, or the final render can exactly reproduce step 7's
    own best point. Measured on the real fixtures (docs/pipeline-tuning.md):
    ~2% of this function's score_alpha calls are exact repeats of an
    already-scored tuple. `scored` below memoizes within this one call only
    (a fresh dict every invocation, never shared or persisted) — this cannot
    change the result: render_text/score_alpha are pure functions of their
    arguments, so a cache hit returns the literal value a fresh computation
    would produce, it just skips redoing that exact work. Exact (unrounded)
    float keys, not rounded ones: a hit only ever occurs when the render
    would have been bit-for-bit identical anyway.

    Returns (size, letter_spacing, baseline_y, x_offset, score).
    """
    score_cache: dict[tuple[float, float, float, float], float] = {}

    def scored(size: float, letter_spacing: float, x_offset: float, baseline_y: float) -> float:
        key = (size, letter_spacing, x_offset, baseline_y)
        cached = score_cache.get(key)
        if cached is not None:
            return cached
        rendered = render_text(text, font_path, size, letter_spacing, (x_offset, baseline_y), canvas_size)
        value = score_alpha(rendered, target_alpha)
        score_cache[key] = value
        return value

    default_baseline = canvas_size[1] * default_baseline_ratio
    grid_step = (region_h * (SIZE_SEARCH_MAX_RATIO - SIZE_SEARCH_MIN_RATIO)) / (SIZE_GRID_STEPS - 1)
    phase_shift = grid_step * size_grid_phase
    size_candidates = np.linspace(
        region_h * SIZE_SEARCH_MIN_RATIO + phase_shift,
        region_h * SIZE_SEARCH_MAX_RATIO + phase_shift,
        SIZE_GRID_STEPS,
    )

    # 1. Coarse grid over size at a fixed default baseline, no per-size baseline fit yet.
    best_coarse_size = float(size_candidates[0])
    best_coarse_score = -1.0
    for size in size_candidates:
        candidate_score = scored(float(size), 0.0, 0.0, default_baseline)
        if candidate_score > best_coarse_score:
            best_coarse_score = candidate_score
            best_coarse_size = float(size)

    # 2. Fit baseline once at the coarse-best size (x still 0 here).
    baseline = _fit_baseline(text, font_path, best_coarse_size, 0.0, 0.0, canvas_size, target_alpha)

    # 2b. Fit x-offset once at the coarse-best size/baseline. Without
    # this, every candidate below gets scored rendered flush at the
    # crop's left edge regardless of where the real ink actually starts
    # (CROP_PADDING_PX plus normal glyph left-bearing) — a near-constant
    # few-px miss that suppresses IoU for every candidate about equally,
    # which is what let a wrong family "win" by a small arbitrary margin.
    x_offset = _coarse_x_offset(text, font_path, best_coarse_size, 0.0, baseline, canvas_size, target_alpha)

    # 3. Refine size via golden-section, baseline and x-offset held fixed.
    refined_size, _ = _refine_scalar(
        lambda size: -scored(size, 0.0, x_offset, baseline),
        max(best_coarse_size * 0.7, 4.0),
        best_coarse_size * 1.3,
        xatol=0.5,
    )

    # 4. Refine letter-spacing via golden-section, size/baseline/x-offset held fixed.
    refined_letter_spacing, _ = _refine_scalar(
        lambda spacing: -scored(refined_size, spacing, x_offset, baseline),
        -LETTER_SPACING_SEARCH_PX,
        LETTER_SPACING_SEARCH_PX,
        xatol=0.1,
    )

    # 5. Final baseline fit at the refined size/letter-spacing.
    final_baseline = _fit_baseline(
        text, font_path, refined_size, refined_letter_spacing, x_offset, canvas_size, target_alpha
    )

    # 6. Refine x-offset via golden-section against score_alpha itself,
    # bracketed around the coarse grid estimate from step 2b.
    refined_x_offset, _ = _refine_scalar(
        lambda x: -scored(refined_size, refined_letter_spacing, x, final_baseline),
        x_offset - X_OFFSET_SEARCH_PX / 2,
        x_offset + X_OFFSET_SEARCH_PX / 2,
        xatol=0.25,
    )

    # 7. One more size refine, narrowly bracketed around what step 3
    # already found, but now using the properly-fit x-offset instead of
    # step 2b's coarse one. Step 3 ran before x-offset was trustworthy,
    # so it could settle on a slightly-off size; this second pass (same
    # "fit once per phase" idea already used for baseline, extended one
    # round further) corrects for that instead of carrying the bias
    # through to the final score.
    refined_size, _ = _refine_scalar(
        lambda size: -scored(size, refined_letter_spacing, refined_x_offset, final_baseline),
        max(refined_size * 0.85, 4.0),
        refined_size * 1.15,
        xatol=0.5,
    )
    final_baseline = _fit_baseline(
        text, font_path, refined_size, refined_letter_spacing, refined_x_offset, canvas_size, target_alpha
    )
    final_score = scored(refined_size, refined_letter_spacing, refined_x_offset, final_baseline)

    return refined_size, refined_letter_spacing, final_baseline, refined_x_offset, final_score


def match_font(text: str, target_alpha: np.ndarray, crop_shape: tuple[int, int], region_h: float) -> MatchResult:
    """Coarse grid -> golden-section refine -> baseline fit, per the brief's stage-3 recipe.

    Each candidate is searched from every starting point in RESTART_CONFIGS,
    keeping whichever converges to the higher score — coordinate descent
    (which _search_candidate does internally) can get stuck in a worse local
    optimum for some candidates than others, which is enough on its own to
    let a wrong font/weight look like the best match.
    """
    canvas_size = (crop_shape[1], crop_shape[0])  # (width, height)

    best: MatchResult | None = None
    all_scores: list[FontCandidateScore] = []

    for candidate in FONT_REGISTRY:
        best_for_candidate: tuple[float, float, float, float, float] | None = None
        for baseline_ratio, size_grid_phase in RESTART_CONFIGS:
            attempt = _search_candidate(
                text, candidate.file_path, canvas_size, region_h, target_alpha, baseline_ratio, size_grid_phase
            )
            if best_for_candidate is None or attempt[-1] > best_for_candidate[-1]:
                best_for_candidate = attempt

        assert best_for_candidate is not None
        size, letter_spacing, baseline_y, x_offset, final_score = best_for_candidate

        all_scores.append(FontCandidateScore(family=candidate.family, weight=candidate.weight, score=final_score))

        if best is None or final_score > best.score:
            best = MatchResult(
                family=candidate.family,
                weight=candidate.weight,
                size=size,
                letter_spacing=letter_spacing,
                baseline_y=baseline_y,
                x_offset=x_offset,
                score=final_score,
                top_candidates=[],
            )

    assert best is not None
    top_candidates = sorted(all_scores, key=lambda c: c.score, reverse=True)[:3]
    best.top_candidates = top_candidates
    return best


def _refine_scalar(objective, lo: float, hi: float, xatol: float = 1e-2) -> tuple[float, float]:
    from scipy.optimize import minimize_scalar

    # scipy's bounded Brent search stands in for a literal golden-section
    # search here — same bracketing, derivative-free approach, well-tested,
    # and (unlike scipy's named 'golden' method) supports hard bounds.
    result = minimize_scalar(objective, bounds=(lo, hi), method="bounded", options={"xatol": xatol})
    return float(result.x), float(result.fun)


BASELINE_SEARCH_STEPS = 6


def _fit_baseline(
    text: str, font_path: str, size: float, letter_spacing: float, x_offset: float, canvas_size: tuple[int, int], target_alpha: np.ndarray
) -> float:
    height = canvas_size[1]
    low = max(height * 0.5, 1.0)
    high = min(height * 0.95, float(height))
    best_baseline = height * 0.8
    best_corr = -1.0
    for baseline_y in np.linspace(low, high, BASELINE_SEARCH_STEPS):
        rendered = render_text(text, font_path, size, letter_spacing, (x_offset, float(baseline_y)), canvas_size)
        if rendered.sum() == 0:
            continue
        row_corr = float(np.corrcoef(rendered.sum(axis=1), target_alpha.sum(axis=1))[0, 1])
        if np.isnan(row_corr):
            continue
        if row_corr > best_corr:
            best_corr = row_corr
            best_baseline = float(baseline_y)
    return best_baseline


def _coarse_x_offset(
    text: str, font_path: str, size: float, letter_spacing: float, baseline_y: float, canvas_size: tuple[int, int], target_alpha: np.ndarray
) -> float:
    """Coarse grid over x-offset against score_alpha itself (mirrors the size search).

    A column-profile correlation proxy (analogous to _fit_baseline's row
    correlation) was tried first and rejected: unlike a word's vertical
    density profile, which is fairly universal across latin fonts at a given
    size, the horizontal column profile IS the word's silhouette, which
    varies a lot between candidates and doesn't reliably peak at the same
    x as the true IoU/SSIM optimum. Scoring the real objective directly,
    same as the size grid, is more expensive but not noisy this way.
    """
    best_x_offset = 0.0
    best_score = -1.0
    for x_offset in np.linspace(-X_OFFSET_SEARCH_PX, X_OFFSET_SEARCH_PX, X_OFFSET_GRID_STEPS):
        rendered = render_text(text, font_path, size, letter_spacing, (float(x_offset), baseline_y), canvas_size)
        candidate_score = score_alpha(rendered, target_alpha)
        if candidate_score > best_score:
            best_score = candidate_score
            best_x_offset = float(x_offset)
    return best_x_offset


def estimate_color(image_bgr: np.ndarray, alpha: np.ndarray, crop_bbox: tuple[int, int, int, int], bg_variance: float) -> ColorResult:
    x0, y0, x1, y1 = crop_bbox
    crop = image_bgr[y0:y1, x0:x1]

    if crop.size == 0 or alpha.size == 0:
        return ColorResult(text_color=(0, 0, 0), background=BackgroundFill(kind="flat", color=(255, 255, 255)))

    def median_color_bgr_to_rgb(mask: np.ndarray) -> tuple[int, int, int] | None:
        if not mask.any():
            return None
        pixels = crop[mask].astype(np.float64)
        med = np.median(pixels, axis=0)
        return (int(med[2]), int(med[1]), int(med[0]))

    text_color = median_color_bgr_to_rgb(alpha > 0.95) or (0, 0, 0)

    if bg_variance < FLAT_BACKGROUND_VARIANCE_THRESHOLD:
        bg_color = median_color_bgr_to_rgb(alpha < 0.05) or (255, 255, 255)
        background = BackgroundFill(kind="flat", color=bg_color)
    else:
        background = _fit_linear_gradient(crop)

    return ColorResult(text_color=text_color, background=background)


def _fit_linear_gradient(crop: np.ndarray) -> BackgroundFill:
    h, w = crop.shape[:2]
    ring_px = min(3, h // 2, w // 2) or 1
    mask = np.zeros((h, w), dtype=bool)
    mask[:ring_px, :] = True
    mask[-ring_px:, :] = True
    mask[:, :ring_px] = True
    mask[:, -ring_px:] = True

    ys, xs = np.nonzero(mask)
    if len(xs) < 3:
        med = np.median(crop.reshape(-1, 3), axis=0)
        return BackgroundFill(kind="flat", color=(int(med[2]), int(med[1]), int(med[0])))

    design = np.stack([xs, ys, np.ones_like(xs)], axis=1).astype(np.float64)
    colors_bgr = crop[ys, xs].astype(np.float64)

    coeffs, _, _, _ = np.linalg.lstsq(design, colors_bgr, rcond=None)
    a, b, c = coeffs[0], coeffs[1], coeffs[2]
    a_avg, b_avg = float(np.mean(a)), float(np.mean(b))
    angle_deg = float(np.degrees(np.arctan2(b_avg, a_avg)))

    def eval_color(px: int, py: int) -> tuple[int, int, int]:
        col = np.clip(a * px + b * py + c, 0, 255)
        return (int(col[2]), int(col[1]), int(col[0]))

    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    projections = sorted(((px * a_avg + py * b_avg, (px, py)) for px, py in corners), key=lambda t: t[0])
    start_px, start_py = projections[0][1]
    end_px, end_py = projections[-1][1]

    stops = [
        GradientStop(position=0.0, color=eval_color(start_px, start_py)),
        GradientStop(position=1.0, color=eval_color(end_px, end_py)),
    ]
    return BackgroundFill(kind="gradient", angle_deg=angle_deg, stops=stops)


def estimate_layout(line_bboxes: list[tuple[float, float, float, float]]) -> LayoutInfo:
    if len(line_bboxes) < 2:
        return LayoutInfo(alignment="left", line_height=None)

    lefts = [b[0] for b in line_bboxes]
    rights = [b[0] + b[2] for b in line_bboxes]
    centers = [b[0] + b[2] / 2 for b in line_bboxes]

    variances = {
        "left": float(np.var(lefts)),
        "center": float(np.var(centers)),
        "right": float(np.var(rights)),
    }
    alignment = min(variances, key=lambda k: variances[k])

    sorted_lines = sorted(line_bboxes, key=lambda b: b[1])
    gaps = [sorted_lines[i + 1][1] - sorted_lines[i][1] for i in range(len(sorted_lines) - 1)]
    line_height = float(np.median(gaps)) if gaps else None

    return LayoutInfo(alignment=alignment, line_height=line_height)


def detect_ui_element(image_bgr: np.ndarray, bbox: tuple[float, float, float, float]) -> UiElement | None:
    img_h, img_w = image_bgr.shape[:2]
    x, y, w, h = bbox

    near_x0 = max(int(x) - UI_ELEMENT_PADDING_PX, 0)
    near_y0 = max(int(y) - UI_ELEMENT_PADDING_PX, 0)
    near_x1 = min(int(x + w) + UI_ELEMENT_PADDING_PX, img_w)
    near_y1 = min(int(y + h) + UI_ELEMENT_PADDING_PX, img_h)
    near_crop = image_bgr[near_y0:near_y1, near_x0:near_x1]
    if near_crop.size == 0:
        return None

    near_gray = cv2.cvtColor(near_crop, cv2.COLOR_BGR2GRAY)
    if float(np.var(near_gray.astype(np.float64))) > UI_ELEMENT_VARIANCE_THRESHOLD:
        return None

    near_median = np.median(near_crop.reshape(-1, 3), axis=0)

    far_x0 = max(int(x) - UI_ELEMENT_FAR_PADDING_PX, 0)
    far_y0 = max(int(y) - UI_ELEMENT_FAR_PADDING_PX, 0)
    far_x1 = min(int(x + w) + UI_ELEMENT_FAR_PADDING_PX, img_w)
    far_y1 = min(int(y + h) + UI_ELEMENT_FAR_PADDING_PX, img_h)
    far_crop = image_bgr[far_y0:far_y1, far_x0:far_x1]
    far_median = np.median(far_crop.reshape(-1, 3), axis=0)

    if float(np.linalg.norm(near_median - far_median)) < UI_ELEMENT_COLOR_DELTA_THRESHOLD:
        return None

    seed_x, seed_y = near_x0, near_y0
    mask = np.zeros((img_h + 2, img_w + 2), dtype=np.uint8)
    flood_image = image_bgr.copy()
    fill_value = (255, 255, 255)
    tol = (FLOOD_FILL_TOLERANCE,) * 3
    try:
        cv2.floodFill(
            flood_image,
            mask,
            (seed_x, seed_y),
            fill_value,
            tol,
            tol,
            flags=cv2.FLOODFILL_MASK_ONLY | (255 << 8),
        )
    except cv2.error:
        return None

    filled = mask[1:-1, 1:-1] > 0
    ys, xs = np.nonzero(filled)
    if len(xs) == 0:
        element_bbox = (float(near_x0), float(near_y0), float(near_x1 - near_x0), float(near_y1 - near_y0))
    else:
        element_bbox = (
            float(xs.min()),
            float(ys.min()),
            float(xs.max() - xs.min() + 1),
            float(ys.max() - ys.min() + 1),
        )

    fill_color = (int(near_median[2]), int(near_median[1]), int(near_median[0]))
    return UiElement(kind="unknown", bbox=element_bbox, fill_color=fill_color)
