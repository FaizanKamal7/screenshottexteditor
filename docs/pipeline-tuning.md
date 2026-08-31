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
