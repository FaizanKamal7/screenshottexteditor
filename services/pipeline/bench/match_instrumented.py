"""Instrumented copy of stages/match.py's match_font/_search_candidate.

Every constant, formula, and decision branch below is copied verbatim from
services/pipeline/stages/match.py (not reimplemented from memory) — the only
additions are counters/recorders. This file changes NOTHING about what gets
computed or in what order; it only observes. Production stages/match.py is
untouched.
"""

from dataclasses import dataclass, field

import cv2
import numpy as np

from fonts.registry import FONT_REGISTRY
from models import FontCandidateScore
from renderer import render_text
from stages.match import MatchResult

IOU_WEIGHT = 0.7
SSIM_WEIGHT = 0.3
SSIM_WIN_SIZE = 7
SSIM_K1 = 0.01
SSIM_K2 = 0.03
SIZE_GRID_STEPS = 7
SIZE_SEARCH_MIN_RATIO = 0.55
SIZE_SEARCH_MAX_RATIO = 1.35
LETTER_SPACING_SEARCH_PX = 2.0
X_OFFSET_SEARCH_PX = 8.0
X_OFFSET_GRID_STEPS = 7
RESTART_CONFIGS: list[tuple[float, float]] = [(0.8, 0.0), (0.72, 0.5)]
BASELINE_SEARCH_STEPS = 6


@dataclass
class CallCounters:
    render_calls: int = 0
    score_calls: int = 0  # score_alpha calls (the expensive SSIM path)
    cache_hits: int = 0
    cache_misses: int = 0

    def reset(self):
        self.render_calls = 0
        self.score_calls = 0
        self.cache_hits = 0
        self.cache_misses = 0


COUNTERS = CallCounters()


def iou(binary_a: np.ndarray, binary_b: np.ndarray) -> float:
    intersection = np.logical_and(binary_a, binary_b).sum()
    union = np.logical_or(binary_a, binary_b).sum()
    if union == 0:
        return 1.0
    return float(intersection) / float(union)


def _box_filter(a: np.ndarray) -> np.ndarray:
    return cv2.boxFilter(a, ddepth=-1, ksize=(SSIM_WIN_SIZE, SSIM_WIN_SIZE))


def _fast_ssim(im1: np.ndarray, im2: np.ndarray, data_range: float = 1.0) -> float:
    if np.any(np.array(im1.shape) < SSIM_WIN_SIZE):
        raise ValueError("win_size exceeds image extent")
    float_type = im1.dtype if im1.dtype in (np.float32, np.float64) else np.float64
    im1 = im1.astype(float_type, copy=False)
    im2 = im2.astype(float_type, copy=False)
    win_size = SSIM_WIN_SIZE
    NP = win_size**2
    cov_norm = NP / (NP - 1)
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
    COUNTERS.score_calls += 1
    if rendered.shape != target.shape:
        raise ValueError("rendered and target alpha must share the same shape")
    binary_rendered = rendered > 0.5
    binary_target = target > 0.5
    iou_score = iou(binary_rendered, binary_target)
    if rendered.size < 49:
        ssim_score = iou_score
    else:
        ssim_score = _fast_ssim(rendered, target, data_range=1.0)
    return IOU_WEIGHT * iou_score + SSIM_WEIGHT * ssim_score


def _refine_scalar(objective, lo: float, hi: float, xatol: float = 1e-2) -> tuple[float, float]:
    from scipy.optimize import minimize_scalar

    result = minimize_scalar(objective, bounds=(lo, hi), method="bounded", options={"xatol": xatol})
    return float(result.x), float(result.fun)


def _fit_baseline(text, font_path, size, letter_spacing, x_offset, canvas_size, target_alpha) -> float:
    height = canvas_size[1]
    low = max(height * 0.5, 1.0)
    high = min(height * 0.95, float(height))
    best_baseline = height * 0.8
    best_corr = -1.0
    for baseline_y in np.linspace(low, high, BASELINE_SEARCH_STEPS):
        COUNTERS.render_calls += 1
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


def _coarse_x_offset(text, font_path, size, letter_spacing, baseline_y, canvas_size, target_alpha) -> float:
    best_x_offset = 0.0
    best_score = -1.0
    for x_offset in np.linspace(-X_OFFSET_SEARCH_PX, X_OFFSET_SEARCH_PX, X_OFFSET_GRID_STEPS):
        COUNTERS.render_calls += 1
        rendered = render_text(text, font_path, size, letter_spacing, (float(x_offset), baseline_y), canvas_size)
        candidate_score = score_alpha(rendered, target_alpha)
        if candidate_score > best_score:
            best_score = candidate_score
            best_x_offset = float(x_offset)
    return best_x_offset


@dataclass
class CandidateTrace:
    family: str
    weight: int
    restart_scores: list[float] = field(default_factory=list)  # one per RESTART_CONFIGS entry
    restart_results: list[tuple] = field(default_factory=list)  # (size, letter_spacing, baseline, x_offset, score)
    coarse_best_scores: list[float] = field(default_factory=list)  # per restart, step-1 coarse score
    chosen_restart_index: int = 0


def _search_candidate_traced(text, font_path, canvas_size, region_h, target_alpha, default_baseline_ratio, size_grid_phase):
    score_cache: dict[tuple[float, float, float, float], float] = {}

    def scored(size, letter_spacing, x_offset, baseline_y) -> float:
        key = (size, letter_spacing, x_offset, baseline_y)
        cached = score_cache.get(key)
        if cached is not None:
            COUNTERS.cache_hits += 1
            return cached
        COUNTERS.cache_misses += 1
        COUNTERS.render_calls += 1
        rendered = render_text(text, font_path, size, letter_spacing, (x_offset, baseline_y), canvas_size)
        value = score_alpha(rendered, target_alpha)
        score_cache[key] = value
        return value

    default_baseline = canvas_size[1] * default_baseline_ratio
    grid_step = (region_h * (SIZE_SEARCH_MAX_RATIO - SIZE_SEARCH_MIN_RATIO)) / (SIZE_GRID_STEPS - 1)
    phase_shift = grid_step * size_grid_phase
    size_candidates = np.linspace(
        region_h * SIZE_SEARCH_MIN_RATIO + phase_shift, region_h * SIZE_SEARCH_MAX_RATIO + phase_shift, SIZE_GRID_STEPS
    )

    best_coarse_size = float(size_candidates[0])
    best_coarse_score = -1.0
    for size in size_candidates:
        candidate_score = scored(float(size), 0.0, 0.0, default_baseline)
        if candidate_score > best_coarse_score:
            best_coarse_score = candidate_score
            best_coarse_size = float(size)

    baseline = _fit_baseline(text, font_path, best_coarse_size, 0.0, 0.0, canvas_size, target_alpha)
    x_offset = _coarse_x_offset(text, font_path, best_coarse_size, 0.0, baseline, canvas_size, target_alpha)

    refined_size, _ = _refine_scalar(
        lambda size: -scored(size, 0.0, x_offset, baseline), max(best_coarse_size * 0.7, 4.0), best_coarse_size * 1.3, xatol=0.5
    )
    refined_letter_spacing, _ = _refine_scalar(
        lambda spacing: -scored(refined_size, spacing, x_offset, baseline), -LETTER_SPACING_SEARCH_PX, LETTER_SPACING_SEARCH_PX, xatol=0.1
    )
    final_baseline = _fit_baseline(text, font_path, refined_size, refined_letter_spacing, x_offset, canvas_size, target_alpha)
    refined_x_offset, _ = _refine_scalar(
        lambda x: -scored(refined_size, refined_letter_spacing, x, final_baseline),
        x_offset - X_OFFSET_SEARCH_PX / 2, x_offset + X_OFFSET_SEARCH_PX / 2, xatol=0.25,
    )
    refined_size, _ = _refine_scalar(
        lambda size: -scored(size, refined_letter_spacing, refined_x_offset, final_baseline),
        max(refined_size * 0.85, 4.0), refined_size * 1.15, xatol=0.5,
    )
    final_baseline = _fit_baseline(text, font_path, refined_size, refined_letter_spacing, refined_x_offset, canvas_size, target_alpha)
    final_score = scored(refined_size, refined_letter_spacing, refined_x_offset, final_baseline)

    return (refined_size, refined_letter_spacing, final_baseline, refined_x_offset, final_score), best_coarse_score


def match_font_traced(text: str, target_alpha: np.ndarray, crop_shape, region_h: float):
    """Same as production match_font(), plus a full per-candidate/per-restart trace."""
    canvas_size = (crop_shape[1], crop_shape[0])

    best: MatchResult | None = None
    all_scores: list[FontCandidateScore] = []
    traces: list[CandidateTrace] = []

    for candidate in FONT_REGISTRY:
        trace = CandidateTrace(family=candidate.family, weight=candidate.weight)
        best_for_candidate = None
        for restart_index, (baseline_ratio, size_grid_phase) in enumerate(RESTART_CONFIGS):
            attempt, coarse_score = _search_candidate_traced(
                text, candidate.file_path, canvas_size, region_h, target_alpha, baseline_ratio, size_grid_phase
            )
            trace.restart_results.append(attempt)
            trace.restart_scores.append(attempt[-1])
            trace.coarse_best_scores.append(coarse_score)
            if best_for_candidate is None or attempt[-1] > best_for_candidate[-1]:
                best_for_candidate = attempt
                trace.chosen_restart_index = restart_index

        traces.append(trace)
        size, letter_spacing, baseline_y, x_offset, final_score = best_for_candidate
        all_scores.append(FontCandidateScore(family=candidate.family, weight=candidate.weight, score=final_score))
        if best is None or final_score > best.score:
            best = MatchResult(
                family=candidate.family, weight=candidate.weight, size=size, letter_spacing=letter_spacing,
                baseline_y=baseline_y, x_offset=x_offset, score=final_score, top_candidates=[], margin=None,
            )

    assert best is not None
    top_candidates = sorted(all_scores, key=lambda c: c.score, reverse=True)[:3]
    best.top_candidates = top_candidates
    best.margin = top_candidates[0].score - top_candidates[1].score if len(top_candidates) > 1 else None
    return best, traces
