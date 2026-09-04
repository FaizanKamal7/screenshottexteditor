# Pipeline tuning log

Starting heuristics for stages 1-2, to be revisited once the 30-fixture
acceptance set (brief section 8) exists. Nothing here is derived from
real screenshot data yet — these are reasonable defaults, not measured
thresholds.

## Stage 1 — Detect (`services/pipeline/stages/detect.py`)

**Block grouping** (`group_into_blocks`): a line starts a new block when
either is true, compared to the previous line:
- vertical gap > `1.5x` the median line height in the image (`BLOCK_GAP_MULTIPLIER`)
- left edge shifts by more than `8px` (`BLOCK_LEFT_EDGE_TOLERANCE_PX`)

Both are arbitrary starting points. The left-edge tolerance in particular
will need to scale with the detected image scale factor (1x/2x/3x) once
that's available earlier in the pipeline — an 8px tolerance is generous
at 1x and tight at 3x.

**Scale factor** (`estimate_scale_factor`): buckets the modal glyph
stroke width (2x the 90th-percentile distance-transform value inside
each alpha mask) into:
- `< 2.2px` → 1x
- `< 4.2px` → 2x
- else → 3x

These bucket edges are guesses based on typical hairline stroke widths
at each scale, not measured from real fixtures.

## Stage 2 — Separate (`services/pipeline/stages/separate.py`)

- `FLAT_BACKGROUND_VARIANCE_THRESHOLD = 15.0` — luminance variance in a
  2px border ring around the region crop, below which the background is
  treated as flat (Otsu + luminance-distance alpha) rather than textured
  (k-means in Lab).
- `MIN_INK_COLUMN_FRACTION = 0.08` — a column counts as "ink" for
  character-box segmentation when its summed alpha exceeds 8% of the
  crop height.
- `MAX_CHAR_GAP_PX = 2` — gaps up to 2px between ink columns are treated
  as anti-aliasing noise within one character, not a character boundary.
  This will under-segment characters with genuinely tight gaps (e.g. "rn")
  and is a known approximation, not a real character segmenter.

## Stage 3 — Match (`services/pipeline/stages/match.py`)

- **Score weights**: `0.7 * IoU + 0.3 * SSIM` (`IOU_WEIGHT`/`SSIM_WEIGHT`) —
  the brief calls for weighting IoU higher; 0.7/0.3 is a starting split,
  not measured.
- **Size search**: coarse grid of `SIZE_GRID_STEPS = 7` sizes spanning
  `0.55x`-`1.35x` of the region's bbox height, then refined with a
  bounded Brent search (`scipy.optimize.minimize_scalar(method="bounded")`)
  standing in for a literal golden-section search — same bracketing,
  derivative-free approach, but supports hard bounds, which scipy's
  named `"golden"` method doesn't. `xatol=0.5px` — sub-pixel size
  precision isn't meaningful, and tightening this only adds renders.
- **Letter-spacing search**: same bounded-search approach, range
  `±2px` (`LETTER_SPACING_SEARCH_PX`), `xatol=0.1px`.
- **Baseline fit**: cross-correlates each candidate baseline's row-profile
  (row-wise alpha sums) against the target mask's row-profile over
  `BASELINE_SEARCH_STEPS = 6` positions spanning `0.5-0.95x` of the crop
  height. Fit **once per phase** (coarse-best size, then again after
  size+letter-spacing refinement) — not on every optimizer evaluation.
  Refitting per-evaluation was the first draft and was reverted: it
  multiplied render count by the baseline search width per objective
  call (thousands of renders per region) and made the objective function
  noisier than golden-section/Brent's unimodality assumption tolerates.
- **UI element detection** (`detect_ui_element`): heuristic only — a
  padded ring around the text is checked for low variance
  (`UI_ELEMENT_VARIANCE_THRESHOLD = 20.0`) and a color delta from a wider
  ring (`UI_ELEMENT_COLOR_DELTA_THRESHOLD = 25.0`); if both trip, a
  flood-fill from just outside the text bbox approximates the element's
  extent. All four thresholds/paddings are guesses, not measurements,
  and the flood-fill seed point (top-left of the padded ring) can miss
  the element entirely on very tightly-fit buttons.

## Stage 4 — Erase (`services/pipeline/stages/erase.py`)

Blends toward the fitted background using the stage-2 alpha mask as the blend
weight (`crop * (1 - alpha) + fill * alpha`), so the erase fades out at the
same anti-aliased edge the original glyph faded in at — no hard cutout.

Only handles `BackgroundFill.kind in {"flat", "gradient"}`, because that's
all `stages/match.py`'s `estimate_color` produces today — a non-flat crop is
always fit as a 2-stop linear gradient, textured/photo backgrounds included.
The brief's LaMa-inpainting fallback for genuinely textured backgrounds is a
real gap, not an oversight: it needs stage 3 to classify "textured"
separately from "gradient" first, which it doesn't yet.

## Stage 5 — Re-render (`services/pipeline/stages/render_stage.py`)

- **Reflow policy**: only `shrink` is implemented (`MIN_SHRINK_RATIO = 0.5`
  — replacement text is scaled down to fit the original crop width, down to
  half the matched size, below which the region is reported as `overflowed`
  in `/render`'s response so the caller can flag it rather than silently
  clipping). `expand`/`wrap`/`truncate` from the brief need layout awareness
  (sibling regions, surrounding UI element bounds) that stage 3 doesn't
  capture yet.
- **Alignment**: `left`/`center`/`right` shift the new text's x-origin
  within the crop to keep the anchor edge fixed as width changes across a
  text substitution. `left` anchors at stage 3's fitted `x_offset` (see
  below); `center`/`right` still compute their anchor from the full crop
  width rather than the original ink's actual extent — a pre-existing
  approximation, not something this round touched.
- `/render` always resends the full edit set against the pristine uploaded
  image (not the previously-rendered output), per the brief's "stateless,
  browser holds document state" — this is what keeps repeated edits to the
  same region from compounding erase/re-render error on top of each other.

## Stage 3 — x-offset fit (added after the round-trip harness existed)

`match_font` used to render every candidate flush at the crop's left edge
(x=0) when scoring. Real ink almost never starts exactly there
(`separate.py`'s `CROP_PADDING_PX` plus normal glyph left-bearing) — a
near-constant few-px horizontal miss that suppressed IoU for every candidate
roughly equally, on text whose stroke widths are themselves often only
1-3px. That's not a minor imprecision: on the synthetic fixture set
(`tests/fixtures/`), it was the dominant cause of wrong-family matches —
nothing scored well, so a small arbitrary difference decided the "winner."

Fix: `x_offset` is now fit like `baseline_y` and `letter_spacing` —
`_coarse_x_offset` (`X_OFFSET_GRID_STEPS = 7` over `±X_OFFSET_SEARCH_PX =
8.0`) against `score_alpha` directly (a column-profile *correlation* proxy
was tried first and rejected — unlike a word's vertical density profile,
which is fairly universal across latin fonts at a given size, the
horizontal column profile is the word's silhouette, which varies too much
between candidates to reliably peak at the true optimum), then refined via
golden-section. A second, narrow size-refine pass was also added after
x-offset is established, since the *first* size refine (step 3) still runs
before x-offset is trustworthy and can otherwise lock in a slightly-off size.

Effect on `tests/test_round_trip.py`'s synthetic fixtures: unflagged
failures dropped from every region essentially being wrong to 3, and those
3 are individually diagnosed, unrelated pre-existing gaps (see
`KNOWN_OPEN_GAPS` in that file) — OCR misreading text, JPEG compression
noise (stage 6), and one borderline button-background case.

**Left open**: even with the *correct* family/weight/size/position, the
achieved `score_alpha` on these fixtures tops out around 0.5-0.7, not the
0.85-0.95 the confidence UI's thresholds (brief section 5) assume. Root
cause, confirmed by brute-force scan: the fixtures are PIL-rendered
"ground truth" being compared against Skia-rendered replacements — two
different rasterizers, different anti-aliasing/hinting, so even a perfect
font/size/position match can't approach IoU/SSIM of 1.0. This isn't
specific to synthetic fixtures — it'll apply to real screenshots too (real
platform renderer vs. our Skia output). Practical implication: the
confidence dot/warning thresholds in `Canvas.tsx` may need recalibrating
against real fixture data rather than assumed as-is, or the round-trip
delta metric and the stage-3 score need to be understood as measuring
related but distinct things rather than expected to move in lockstep.
Also separately noted: `match_font`'s successive-1D-refine search
(coordinate descent — size, then letter-spacing, then x-offset, with one
extra size pass) doesn't reliably converge to the true best score for the
*correct* candidate even when that ceiling is known (see the comment on
`test_match_font_recovers_known_family_and_close_size` in
`tests/test_match.py`) — it can settle on a worse, wrong-weight local
optimum instead. A joint or multi-start search would likely fix this;
another sequential refine pass is a diminishing-returns patch, not a fix.

## Stage 3 — match_font performance investigation

`match_font`'s ~11 candidates x 2 restarts x ~30-90 renders/scores per
region (see "known gaps" below) was profiled on the real fixtures in
`tests/fixtures/` (not synthetic ones) to find out where the time actually
goes, before changing anything. cProfile against `web_3x_dashboard.jpg`
and `ios_3x_login.png` found SSIM (`skimage.metrics.structural_similarity`,
called from `score_alpha`) at 73-83% of total time — Skia rendering itself
barely registered (~13%). That's the opposite of what the architecture
notes above assumed (rendering/candidate-count as the cost driver).

**Two ideas were tried and rejected before landing on what's below** —
kept here so they aren't retried without re-reading why:

- **Cheap candidate prefilter** (rank all 11 candidates with one fast
  coarse-only pass, full-search only the top few): on
  `tests/test_match.py`'s own fixture, the *correct* candidate scored dead
  last (0.19) in the cheap pass despite being the true best (0.64) after
  the full search — even after strengthening the cheap pass with
  baseline+x-offset fitting, it still ranked 6th of 11. The score
  landscape is too sharply peaked around a properly-fit baseline/offset
  for any cheap proxy to predict winners. Reverted.
- **Match once per detected block, reuse for sibling lines**: passed the
  packaged test suite, but broke on `web_3x_dashboard.jpg` specifically —
  stat-card labels and values (`$482,910` next to `Revenue`) land in the
  same paragraph-proximity "block" but are genuinely different font
  weights; forcing them to share one font search made pixel error *worse*
  (one region's delta went from 3.6 to 27.9). `group_into_blocks`'s
  grouping is a layout signal, not a font-identity one. Reverted.

**What shipped, both verified bit-exact/behavior-preserving against the
real fixtures before being wired in (not just synthetic tests):**

- **`_fast_ssim`** (`stages/match.py`): a direct reimplementation of
  skimage's exact SSIM formula (verified against its installed 0.26.0
  source, not assumed — `win_size=7`, `scipy.ndimage.uniform_filter`,
  `mode='reflect'`, `K1=0.01/K2=0.03`, `use_sample_covariance=True`),
  skipping skimage's generic dispatch/validation overhead. Verified
  bit-exact (max abs diff `0.0`) across 34,369 real (rendered, target)
  pairs captured from actual `match_font()` runs on every region in every
  fixture, and the resulting `MatchResult` was identical on all 34
  regions. Real-world speedup, measured unprofiled (not from cProfile,
  which overstated it — see below): only ~1-7%, not the ~23% cProfile
  suggested. cProfile's own per-call instrumentation overhead scales with
  a function's number of internal sub-calls, and skimage's SSIM makes many
  small ones (isinstance checks, dtype dispatch), which inflated its
  apparent share of the cost under profiling. Kept anyway — real,
  zero-risk, just modest.
- **Per-call memoization inside `_search_candidate`**: the coarse-to-fine
  search sometimes evaluates the exact same `(size, letter_spacing,
  x_offset, baseline_y)` tuple more than once (e.g. step 7's converged
  size landing on a point step 3 already tried). Measured on all 34 real
  fixture regions (748 candidate-restart searches, 47,833 renders): 6.26%
  of all renders are exact intra-search duplicates, but only 2.12% of
  `score_alpha` (the expensive part) calls are — most duplicates repeat a
  cheap baseline-fit render (which never needed SSIM in the first place),
  not an already-scored one. A cache scoped to one `_search_candidate`
  call only (fresh dict per call, exact float keys, never shared) skips
  the repeat. Verified: all 34 regions' `MatchResult` bit-identical to the
  pre-memoization baseline. Measured speedup: 3.9% aggregate across all 34
  regions (26.27s -> 25.28s) — but *not* consistently positive per
  fixture: on `web_3x_dashboard.jpg` alone it measured slightly slower
  (0.965x) since that fixture's search happened to hit fewer duplicates
  and the cache's own dict overhead outweighed what little it saved. Kept
  since it's zero-risk (a cache miss just falls back to the identical
  fresh computation), but it should not be reported as a reliable win on
  every fixture.
- **Investigated and explicitly rejected**: a cheap IoU-only upper bound
  (`0.7*iou + 0.3*1.0`, SSIM's theoretical max) to skip SSIM when it
  provably can't beat the running best in the coarse grids — only 0.3-0.5%
  of coarse-grid evals ever satisfy it, not worth the complexity. Early
  stopping in the golden-section refines — logged score sequences show
  genuinely non-monotonic behavior within a single refine (score jumping
  0.42 -> 0.82 -> 0.57 across consecutive evaluations on real fixture
  data), so no early-stop rule was found that's provably safe without
  risking the same class of silent regression the two reverted ideas
  above already demonstrated.

Net effect of both shipped changes together: real, verified-safe, but
modest (single-digit percent) — `match_font`'s true bottleneck is the
`uniform_filter`-based SSIM computation itself (5 windowed stats x 2
passes per evaluation), which is inherent to the metric, not overhead.
Meaningfully faster would require changing what gets computed or how many
evaluations run — both explored above and found to carry real accuracy
risk without much more validation than this round covered.

### Rejected: IoU-only search objective, SSIM only for final ranking

Tried as a controlled experiment (`stages/match_experimental.py`, deleted —
never wired into `main.py`): use IoU alone as the coarse-grid/golden-section
objective throughout `_search_candidate`, and compute the real
`0.7*IoU+0.3*SSIM` blended score only once per (candidate, restart), for
comparing candidates/restarts against each other. Structurally identical
to production otherwise — same candidates, ordering, 2-restart strategy,
iteration counts, weights.

**The speedup is real and large**: 97.8% fewer SSIM calls (33,642 ->
748 across the 34 real fixture regions), 2.39x aggregate wall-clock
speedup on `match_font()`.

**But it changes results, and mostly for the worse.** Across all 34 real
fixture regions: 0 identical to the SSIM-guided baseline. 11 picked a
different font *family* entirely; 4 picked a different weight; the
remaining 19 kept family/weight but converged to different geometry
(size/spacing/baseline/x-offset). Round-trip pixel delta regressed on 18
regions and improved on 9 — net negative, and the regressions aren't
uniformly small: `web_3x_dashboard.jpg`'s `$482,910` (already one of the
six pre-existing `KNOWN_OPEN_GAPS` failures, borderline at delta 3.6 in
production) went to delta 17.4 under the experimental path — a known-hard
case made drastically worse, not better.

**Why**: a candidate-by-candidate comparison (not just region winners —
every one of the 242 sampled candidate-restart searches on
`web_3x_dashboard.jpg` and `ios_3x_login.png`) found 75.6% converged to a
*meaningfully different geometry* under IoU-only search than under the
real search, with the resulting blended score sometimes differing by more
than 0.3 for the same candidate. SSIM is not a final-ranking-only
refinement on top of an IoU-driven trajectory — it actively steers which
local optimum the golden-section search lands in. Dropping it from the
search changes *where the search goes*, not just how the destination gets
scored.

Verdict: not safe for production as tested. The premise the optimization
was built on ("SSIM only matters for the final comparison") is directly
falsified by the candidate-level data. A narrower version — SSIM-guided
throughout but with fewer evaluations, or a cheaper proxy validated per
candidate rather than globally — might still be viable, but this
particular formulation isn't.

### Follow-up investigation: reducing match_font's computational cost without heuristics

After the above, a further design/research-only pass investigated whether
the *same* exact search (candidates, restarts, ranges, SSIM-guided
objective) could be made cheaper without touching what it computes or how
many evaluations it runs — as opposed to the ideas above, which all tried
to change the search itself. Five areas were investigated empirically
(instrumented real runs across all 34 fixture regions, wall-clock timing,
never cProfile): separating font-identity ranking from cheap geometric
parameter narrowing, restructuring the search's internal decomposition,
accelerating the SSIM computation itself, accelerating Skia rasterization,
and reformulating the parameter search as a joint optimization. Most were
rejected by real data:

- **Geometry-based search-bracket narrowing**: disqualified. Across all
  748 real (candidate, restart) searches, converged size lands outside
  production's own coarse-grid range (0.55x-1.35x of `region_h`) in 12/748
  (1.6%) cases, and converged x-offset lands outside the current ±8px range
  in 129/748 (17%) cases — production's own two-phase refine (coarse pick
  -> dynamic bracket around it) already lets the true optimum drift past
  the nominal grid on real data, so no geometry-only estimate at or below
  current width is safe.
- **Search decomposition** (candidate -> cheap estimate -> SSIM-refine ->
  final score): inherits the same disqualification as above for its cheap
  estimate step; doesn't fix the known sequential-coordinate-descent
  local-optima weakness either (see `test_match.py`'s
  `test_match_font_recovers_known_family_and_close_size` comment) — a
  joint optimizer does fix that (see below) but at more evaluations, not
  fewer.
- **Joint parameter optimization** (`scipy.optimize.minimize`,
  Nelder-Mead/Powell, over size/letter_spacing/x_offset jointly instead of
  sequential coordinate descent): Powell gives a real quality improvement
  over the current sequential refine (68% of 748 real searches reach an
  equal-or-better score, positive median delta) — confirming the
  coordinate-descent local-optima gap noted in `test_match.py` is real —
  but costs 2.18x more `score_alpha` evaluations, the opposite of a speed
  win. Restarts remain necessary even under joint optimization (a
  single-restart joint search matches only 44% of production's
  best-of-two-restarts result). Not pursued for performance; the quality
  signal is a separate, unaddressed lead.
- **Skia surface reuse** in `render_text` (one surface reused across calls
  instead of a fresh `skia.Surface` per call): measured *slower*
  (0.45x) — reusing a max-sized surface forces every `toarray()` call to
  pull the full worst-case buffer instead of one sized to that call's
  actual (usually smaller) canvas. Rejected; a caution against shipping
  this on intuition without measuring.
- **Integral-image SSIM** (`cv2.integral`, turning windowed sums into O(1)
  lookups): measured slower (0.67-0.75x) than the direct filter at the
  array sizes real regions actually produce (median ~5,900px) — the
  per-call setup/lookup overhead across 5 separate integral images
  outweighs the benefit at this scale. Rejected.
- **numba njit SSIM**: correct but dominated by the shipped alternative
  below (slower, adds a ~64MB dependency, ~2.4s one-time JIT compile cost
  relevant to a request-scoped/Cloud Run cold start). Not pursued.
- **Skia A8 alpha-only surface** (render directly to an alpha-only
  surface, skip the RGBA roundtrip `toarray()` currently does): real,
  2.99x faster in isolation, ~1.21x on full `match_font` wall-clock,
  winning family/weight unchanged across all 34 regions — but not
  bit-exact: `MatchResult` differs at a real (not float-noise) magnitude
  in 12/34 regions (~1e-5, still far under any `xatol`). Touches shared
  `renderer.py`, used by other callers not exercised by this
  investigation (e.g. `stages/render_stage.py`). **Deliberately not
  implemented in this round** — flagged for a separate follow-up with a
  broader regression set and an audit of every `render_text` caller before
  deciding whether to ship it. **Update: implemented in a later round, see
  "Shipped: Skia A8 alpha-only rendering in `renderer.py`" below.**

**What was implemented**: replacing `_fast_ssim`'s 5
`scipy.ndimage.uniform_filter(size=7)` calls with `cv2.boxFilter` (same
box-mean math, OpenCV already a production dependency via paddleocr's
`opencv-contrib-python` pin). Border-mode mismatch between scipy's default
`'reflect'` and cv2's default `BORDER_REFLECT_101` turns out not to
matter: `_fast_ssim` always crops `pad=(win_size-1)//2=3` rows/cols off
the final SSIM map before averaging, and a size-7 filter's output only
touches border-extended input within 3px of an edge — exactly the region
the crop discards. Confirmed both by this reasoning and empirically
(`BORDER_REFLECT`/`BORDER_REFLECT_101` gave bit-identical `_fast_ssim`
output in testing).

Validated against all 34 real regions (not a sample): direct old-vs-new
`_fast_ssim` comparison on 33,642 real captured `(rendered, target)` pairs
— max abs diff `3.058e-08`, mean `2.778e-09` (float-noise level, not a
real perturbation). Full `MatchResult` comparison, old vs new, all 34
regions: **0/34 family changes, 0/34 weight changes**; size/letter-spacing/
x-offset/score deltas all in the `1e-8`-`1e-9` range; `baseline_y`
bit-identical (0.0 diff — it's fit via a row-correlation proxy, not
`score_alpha`, so it never touches `_fast_ssim`). Full test suite: 40/40
non-round-trip tests pass; the round-trip accuracy gate's failure is
pre-existing (reproduced identically — same fixtures/text/mean_delta/score
to ~1e-9 — with the original `scipy.uniform_filter` restored, confirming
it predates and is unrelated to this change; it's the already-in-progress
PaddleOCR migration's stale `KNOWN_OPEN_GAPS` entries, not a regression
from this change).

Wall-clock, all 34 regions: **26.334s -> 18.436s, 1.428x** aggregate
speedup. Per-fixture range 1.259x (`android_1x_button.png`) to 1.579x
(`ios_3x_login.png`) — consistently positive on every fixture, unlike the
memoization change above.

### Shipped: Skia A8 alpha-only rendering in `renderer.py`

Follow-up to the A8 idea flagged above: `render_text()` (`services/pipeline/renderer.py`)
now renders directly into an alpha-only Skia surface instead of a full RGBA
surface with a channel-3 extraction —
`skia.Surface.MakeRaster(skia.ImageInfo.MakeA8(width, height))` +
`canvas.clear(0)` in place of `skia.Surface(width, height)` +
`canvas.clear(skia.ColorTRANSPARENT)`, and `image.toarray()` (already
`(height, width)`, no slicing) in place of
`image.toarray(colorType=skia.kRGBA_8888_ColorType)[:, :, 3]`. No other file
changed — all four `render_text` call sites (three in `stages/match.py`:
`_search_candidate`, `_fit_baseline`, `_coarse_x_offset`; one in
`stages/render_stage.py`: `compose_region`) pick up the change with no
caller-side edits.

Validated against all 34 real fixture regions (`tests/fixtures/`, same
regions the `_fast_ssim`/`cv2.boxFilter` change above was validated
against), A8 vs. the pre-change RGBA implementation:

- **Full test suite**: 40/40 non-round-trip tests pass on both. The
  round-trip gate's one failing assertion is byte-for-byte the same set on
  both — same 6 unflagged fixtures/lines, same `mean_delta`/`score` to full
  float precision (e.g. `windows_1x_dialog.png` / `"Choose how updates are
  installed"`: `6.0416401780038145, 0.880859598412105` under both).
  Reproduced via a direct A/B (A8 renderer vs. the prior RGBA renderer
  restored, all other files unchanged) to rule out any interaction with the
  already-in-progress PaddleOCR migration gaps tracked in
  `KNOWN_OPEN_GAPS` — identical either way.
- **`MatchResult` comparison, all 34 regions**: **0/34 family changes, 0/34
  weight changes**, 22/34 bit-identical results. Of the remaining 12:
  size delta max `1.533e-05`, letter-spacing delta max `1.013e-04`,
  x-offset delta max `2.034e-05`, score delta max `6.927e-06` — all
  several orders of magnitude under the search's own `xatol` (0.5px size,
  0.1px letter-spacing, 0.25px x-offset). `baseline_y` bit-identical
  (`0.0` diff) on every region, expected since it's fit by picking the best
  of `BASELINE_SEARCH_STEPS = 6` discrete grid points via row-correlation —
  differences this small never flip which grid point wins.
- **Round-trip gate at region granularity**: comparing each of the 34
  regions' `mean_delta < 2.0` pass/fail individually between A8 and RGBA —
  **0/34 flips**.
- **Final compositing** (`compose_region`, using each region's actual
  converged `MatchResult`): 6/34 regions show any pixel difference at all;
  max delta is exactly `1.0` on the 0-255 scale (i.e. exactly ±1/255,
  consistent with A8 writing coverage directly vs. RGBA's extra
  SRC_OVER-blend-then-round step); mean delta across all 34 regions'
  patches `0.000107`; `0.005%` of pixels affected. No round-trip gate
  result changes (see above).
- **Performance** (warm `time.perf_counter()`, three independent repeated
  runs inside the container, never cProfile):
  - `render_text()` itself, ~47,100 real calls/run: median `0.072-0.075ms`
    (A8) vs. `0.143-0.147ms` (RGBA) — consistently ~2.0x per call. Summed
    across all three runs: `20.64s` (A8) vs. `29.68s` (RGBA), **1.438x**.
  - `match_font()`, all 34 regions, summed across all three runs: `52.40s`
    (A8) vs. `61.53s` (RGBA), **1.174x** aggregate. Per-fixture range
    `1.066x` (`web_1x_pricing.jpg`) to `1.252x` (`android_2x_profile.jpg`).
    Lower than this idea's original ~1.21x estimate above — plausibly
    because that estimate predates the `cv2.boxFilter` SSIM change also
    documented in this file, which already cut into `score_alpha`'s share
    of `match_font`'s wall-clock; with SSIM cheaper, `render_text`'s
    remaining RGBA overhead is a smaller fraction of the total than it was
    when A8 was first measured, so removing it now buys proportionally
    less.
  - `compose_region()`: `0.068s` (A8) vs. `0.078s` (RGBA) summed across
    three runs, **1.144x** — noisy at this sample size (34 single-call
    regions per run; per-run ratios ranged `1.05x-1.24x`), so treat the
    combined number as the more reliable one, not any single run.
  - Confirmed the same each run: `render_text`'s three-part return
    contract (shape `(height, width)`, dtype `float32`, values in `[0,
    1]`) held on every one of ~47,100+ calls per run, both before and
    after.

**Caveat inherited from the original investigation, still true**: all
validation above runs against the 8 synthetic seed fixtures
(`generate_synthetic_fixtures.py`), not real device screenshots — the
30-fixture real-device set called for in the brief doesn't exist yet.

### Combined benchmark: cv2.boxFilter + Skia A8 together, full `/analyze` pipeline

Both optimizations above were measured in isolation (`match_font()`/
`render_text()` microbenchmarks). This is a final measurement of their
*combined* effect through the real `/analyze` pipeline — not the product of
the two isolated speedups, measured directly. No code changed for this
round; it's purely measurement of the already-shipped state.

**Method**: three on-disk configurations, each run through `main.py`'s
actual `_run_analysis()` generator (same `ProcessPoolExecutor`, same
detect → separate → match → color → UI → layout stages the `/analyze`
endpoint drives — only the HTTP/auth layer skipped) against all 8 real
fixtures in `tests/fixtures/`, one cold first call plus 3 warm repeats per
fixture, reading the pipeline's own built-in `analyze_timings` log line
(`main.py`'s `_log_analyze_timings`) rather than adding new instrumentation:

- **Original baseline**: `git show HEAD`'s `stages/match.py` (skimage
  `structural_similarity`, no memoization) + `git show HEAD`'s
  `renderer.py` (RGBA surface).
- **After cv2.boxFilter**: current `stages/match.py` (`_fast_ssim` +
  memoization) + `git show HEAD`'s `renderer.py` (RGBA surface) — the
  state actually shipped, in order, right before A8.
- **Combined current** (= "after A8", production today): current
  `stages/match.py` + current `renderer.py` (A8 surface). There is no
  separate "A8 without boxFilter" production state to measure — A8 was
  built on top of an already-boxFilter'd `match.py`.

| Metric | Original baseline | After cv2.boxFilter | After A8 (= combined current) |
|---|---:|---:|---:|
| Aggregate warm pipeline time (8 fixtures, sum of per-fixture medians) | 16.006s | 13.369s | **12.326s** |
| Median per-fixture total time | 1.819s | 1.604s | **1.527s** |
| Speedup vs original | 1.00x | 1.197x | **1.298x** |
| Speedup vs previous state | — | 1.197x | **1.085x** |
| `font_matching_cpu_s` aggregate (production's own per-request metric) | 27.548s | 19.218s | 16.219s |
| `detect_wall_s` aggregate (OCR — untouched by either change) | 7.343s | 7.365s | 7.305s |
| `render_text` calls (34 regions, 8 fixtures) | 47,833 | 47,106 | 47,100 |
| SSIM evaluations | 34,369 | 33,642 | 33,636 |
| Regions detected | 34 | 34 | 34 |

`detect_wall_s` staying flat across all three states is the expected
control: OCR detection is untouched by either optimization, so its cost
shouldn't move, and it doesn't. The remaining gap between `font_matching_cpu_s`'s
speedup (1.70x original-to-combined) and full pipeline speedup (1.30x) is
OCR's now-larger fixed share of total request time, plus per-request
`ProcessPoolExecutor` scheduling overhead that neither change touches.

**Cold-start impact**: cold first-call `total_request_s` was 4.84s / 4.75s /
4.65s (original / boxFilter / combined) — essentially flat, dominated by
~2.7-3.0s of PaddleOCR `engine_init_s` plus process-pool spawn, neither of
which either optimization touches. Only steady-state warm cost moved.

**Correctness**: full suite 40/40 non-round-trip tests pass on the combined
(production) state; the round-trip gate's one failure is the same 6
unflagged fixture/line pairs as always (see `KNOWN_OPEN_GAPS` in
`tests/test_round_trip.py`); all 34 regions detected identically in every
state; 0 unexpected `MatchResult` changes (see the A8 section above for the
full family/weight/geometry comparison).

**Verdict**: combined effect is real, directly measured, and safe to adopt
as the new production performance baseline — no regressions found anywhere
in the stack.

## Known gaps

- Per-character boxes are derived from vertical projection on the alpha
  mask, not from OCR or font metrics. It's a placeholder good enough for
  stage 3's render-and-compare scoring, not a precise glyph segmenter.
- `Region.confidence` now holds the real stage-3 match score (was
  PaddleOCR's raw recognition confidence through step 2).
- Stage 3's matcher is unoptimized: roughly 30-40 renders per font
  candidate (~11 candidates in the registry today) per region, all
  synchronous inside the `/analyze` request. No caching, no parallelism.
  Acceptable for now; revisit if/when the font registry grows or latency
  becomes a real product concern — the vision-model platform prior
  (deferred, see brief section 3) would help here by re-ordering
  candidates so likely matches get found without walking the full list.
