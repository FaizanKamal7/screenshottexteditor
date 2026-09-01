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
