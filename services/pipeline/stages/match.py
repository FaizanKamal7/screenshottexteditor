from dataclasses import dataclass

import cv2
import numpy as np
from skimage.metrics import structural_similarity

from fonts.registry import FONT_REGISTRY
from models import BackgroundFill, FontCandidateScore, GradientStop, UiElement
from renderer import render_text

IOU_WEIGHT = 0.7
SSIM_WEIGHT = 0.3

SIZE_GRID_STEPS = 7
SIZE_SEARCH_MIN_RATIO = 0.55
SIZE_SEARCH_MAX_RATIO = 1.35

LETTER_SPACING_SEARCH_PX = 2.0

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


def score_alpha(rendered: np.ndarray, target: np.ndarray) -> float:
    if rendered.shape != target.shape:
        raise ValueError("rendered and target alpha must share the same shape")
    binary_rendered = rendered > 0.5
    binary_target = target > 0.5
    iou_score = iou(binary_rendered, binary_target)

    if rendered.size < 49:  # skimage's default win_size (7) needs >=7px per side
        ssim_score = iou_score
    else:
        ssim_score = float(structural_similarity(rendered, target, data_range=1.0))

    return IOU_WEIGHT * iou_score + SSIM_WEIGHT * ssim_score


def match_font(text: str, target_alpha: np.ndarray, crop_shape: tuple[int, int], region_h: float) -> MatchResult:
    """Coarse grid -> golden-section refine -> baseline fit, per the brief's stage-3 recipe.

    Baseline is fit once per phase (not on every golden-section evaluation):
    refitting it inside every objective call would multiply the render count
    by the baseline search width and also make the objective noisier than
    golden-section's unimodality assumption tolerates.
    """
    canvas_size = (crop_shape[1], crop_shape[0])  # (width, height)
    default_baseline = canvas_size[1] * 0.8  # reasonable guess for coarse ranking only
    size_candidates = np.linspace(
        region_h * SIZE_SEARCH_MIN_RATIO, region_h * SIZE_SEARCH_MAX_RATIO, SIZE_GRID_STEPS
    )

    best: MatchResult | None = None
    all_scores: list[FontCandidateScore] = []

    for candidate in FONT_REGISTRY:
        # 1. Coarse grid over size at a fixed default baseline, no per-size baseline fit yet.
        best_coarse_size = float(size_candidates[0])
        best_coarse_score = -1.0
        for size in size_candidates:
            rendered = render_text(text, candidate.file_path, size, 0.0, (0.0, default_baseline), canvas_size)
            candidate_score = score_alpha(rendered, target_alpha)
            if candidate_score > best_coarse_score:
                best_coarse_score = candidate_score
                best_coarse_size = float(size)

        # 2. Fit baseline once at the coarse-best size.
        baseline = _fit_baseline(text, candidate.file_path, best_coarse_size, 0.0, canvas_size, target_alpha)

        # 3. Refine size via golden-section, baseline held fixed.
        refined_size, _ = _refine_scalar(
            lambda size: -score_alpha(
                render_text(text, candidate.file_path, size, 0.0, (0.0, baseline), canvas_size), target_alpha
            ),
            max(best_coarse_size * 0.7, 4.0),
            best_coarse_size * 1.3,
            xatol=0.5,
        )

        # 4. Refine letter-spacing via golden-section, size and baseline held fixed.
        refined_letter_spacing, refined_neg_score = _refine_scalar(
            lambda spacing: -score_alpha(
                render_text(text, candidate.file_path, refined_size, spacing, (0.0, baseline), canvas_size),
                target_alpha,
            ),
            -LETTER_SPACING_SEARCH_PX,
            LETTER_SPACING_SEARCH_PX,
            xatol=0.1,
        )

        # 5. Final baseline fit at the refined size/letter-spacing.
        final_baseline = _fit_baseline(
            text, candidate.file_path, refined_size, refined_letter_spacing, canvas_size, target_alpha
        )
        final_rendered = render_text(
            text, candidate.file_path, refined_size, refined_letter_spacing, (0.0, final_baseline), canvas_size
        )
        final_score = score_alpha(final_rendered, target_alpha)

        all_scores.append(FontCandidateScore(family=candidate.family, weight=candidate.weight, score=final_score))

        if best is None or final_score > best.score:
            best = MatchResult(
                family=candidate.family,
                weight=candidate.weight,
                size=refined_size,
                letter_spacing=refined_letter_spacing,
                baseline_y=final_baseline,
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
    text: str, font_path: str, size: float, letter_spacing: float, canvas_size: tuple[int, int], target_alpha: np.ndarray
) -> float:
    height = canvas_size[1]
    low = max(height * 0.5, 1.0)
    high = min(height * 0.95, float(height))
    best_baseline = height * 0.8
    best_corr = -1.0
    for baseline_y in np.linspace(low, high, BASELINE_SEARCH_STEPS):
        rendered = render_text(text, font_path, size, letter_spacing, (0.0, float(baseline_y)), canvas_size)
        if rendered.sum() == 0:
            continue
        row_corr = float(np.corrcoef(rendered.sum(axis=1), target_alpha.sum(axis=1))[0, 1])
        if np.isnan(row_corr):
            continue
        if row_corr > best_corr:
            best_corr = row_corr
            best_baseline = float(baseline_y)
    return best_baseline


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
