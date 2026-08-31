# Font licensing

We do not bundle or serve SF Pro, Segoe UI, Helvetica, or any other
proprietary platform font. The pipeline only ever renders with openly
licensed substitutes, installed via `apt-get` in
`services/pipeline/Dockerfile` (`fonts-inter`, `fonts-roboto`,
`fonts-liberation`, `fonts-noto-core`) and registered in
`services/pipeline/fonts/registry.py`.

| Platform font (never used) | Open substitute we render with | Notes |
|---|---|---|
| SF Pro (iOS / macOS) | **Inter** | Metric differences exist; Inter is the closest widely-used open substitute. |
| Helvetica | **Inter** | Same substitute as SF Pro — both are geometric/grotesque sans faces close enough for UI text matching. |
| Roboto (Android) | **Roboto** | This one's the real thing — Roboto itself is open (Apache 2.0) and ships via `fonts-roboto`. |
| Arial | **Liberation Sans** | Purpose-built metric-compatible clone of Arial; this is the most faithful substitution in the registry. |
| Segoe UI (Windows) | **Noto Sans** | No true open metric clone of Segoe UI exists. Noto Sans is used as a reasonable visual stand-in, not a metric match — flagged here honestly rather than silently passed off as equivalent. |
| Any wide-script text | **Noto Sans** | Also the general fallback for coverage beyond Latin, though script support beyond Latin is out of scope for v1 (see brief section 6). |

**UI labeling requirement**: whenever a match result is shown to a user
(debug panel now; the font override panel in a later step), the label
must show the *substitute* font name actually used (e.g. "Inter"), not
a claim that it's "SF Pro." `Region.font_family` in the API response
already reflects this — it's always one of the registry's real family
names.

**Licenses**: Inter (SIL OFL 1.1), Roboto (Apache 2.0), Liberation
Sans (SIL OFL 1.1), Noto Sans (SIL OFL 1.1) — all free to bundle,
serve, and use in a commercial product.

**Future desktop build**: per the brief, a desktop build can read the
user's installed fonts and match against those directly, potentially
including the real platform font. Not applicable to the web service.
