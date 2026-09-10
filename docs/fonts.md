# Font licensing

We do not bundle or serve SF Pro, Segoe UI, Helvetica, or any other
proprietary platform font. The pipeline only ever renders with openly
licensed substitutes, installed in `services/pipeline/Dockerfile` — most
via `apt-get` (`fonts-inter`, `fonts-roboto`, `fonts-liberation`,
`fonts-noto-core`, `fonts-texgyre`), one (Selawik, not packaged for Debian)
vendored directly from its pinned upstream GitHub release — and registered
in `services/pipeline/fonts/registry.py`.

| Platform font (never used) | Open substitute we render with | Notes |
|---|---|---|
| SF Pro (iOS / macOS) | **Inter** | Metric differences exist; Inter is the closest widely-used open substitute. No verified real-metric-clone alternative found. |
| Helvetica | **TeX Gyre Heros** | Purpose-built metric-compatible Helvetica clone (built on URW Nimbus Sans L, GUST Font License — free, LPPL-equivalent). Used to share Inter's substitute above; split out once a real metric clone was available — see `docs/pipeline-tuning.md`. Measured cap-height ratio 0.729 (fontTools, not a public-table guess). |
| Roboto (Android) | **Roboto** | This one's the real thing — Roboto itself is open (Apache 2.0) and ships via `fonts-roboto`. |
| Arial | **Liberation Sans** | Purpose-built metric-compatible clone of Arial; this is the most faithful substitution in the registry. |
| Segoe UI (Windows) | **Selawik** | Microsoft's own official open-source (SIL OFL 1.1) font, purpose-built as a metrics-compatible Segoe UI replacement (github.com/microsoft/Selawik). That compatibility claim covers glyph advance widths/line spacing, not verified cap-height — so unlike TeX Gyre Heros above, `fonts/registry.py`'s size-hint feature doesn't yet apply a correction for it (no real Segoe UI file available here to verify one against). Replaces Noto Sans's previous role as the "not a real metric match" stand-in. |
| Any wide-script text | **Noto Sans** | General fallback for coverage beyond Latin, though script support beyond Latin is out of scope for v1 (see brief section 6). No longer used as the Segoe UI stand-in now that Selawik fills that role. |

**UI labeling requirement**: whenever a match result is shown to a user
(debug panel now; the font override panel in a later step), the label
must show the *substitute* font name actually used (e.g. "Inter"), not
a claim that it's "SF Pro." `Region.font_family` in the API response
already reflects this — it's always one of the registry's real family
names.

**Licenses**: Inter (SIL OFL 1.1), Roboto (Apache 2.0), Liberation
Sans (SIL OFL 1.1), Noto Sans (SIL OFL 1.1), TeX Gyre Heros (GUST Font
License — free, LPPL-equivalent), Selawik (SIL OFL 1.1) — all free to
bundle, serve, and use in a commercial product.

**Future desktop build**: per the brief, a desktop build can read the
user's installed fonts and match against those directly, potentially
including the real platform font. Not applicable to the web service.
