from dataclasses import dataclass
from typing import Literal

# Which real, licensed platform font each candidate stands in for.
# Purely informational (docs/UI labeling) — never used by the matcher itself.
StyleRole = Literal["sf_pro", "helvetica", "android", "arial", "wide_coverage", "segoe_ui"]


@dataclass(frozen=True)
class FontCandidate:
    family: str
    weight: int
    style_role: StyleRole
    file_path: str


FONT_REGISTRY: list[FontCandidate] = [
    # Inter — substitute for SF Pro (iOS/macOS). Used to also stand in for
    # Helvetica before TeX Gyre Heros (below) was added as a dedicated,
    # metric-compatible substitute for it — see docs/fonts.md.
    FontCandidate("Inter", 400, "sf_pro", "/usr/share/fonts/opentype/inter/Inter-Regular.otf"),
    FontCandidate("Inter", 500, "sf_pro", "/usr/share/fonts/opentype/inter/Inter-Medium.otf"),
    FontCandidate("Inter", 600, "sf_pro", "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"),
    FontCandidate("Inter", 700, "sf_pro", "/usr/share/fonts/opentype/inter/Inter-Bold.otf"),
    # Roboto — substitute for Android's default UI font.
    FontCandidate("Roboto", 400, "android", "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Regular.ttf"),
    FontCandidate("Roboto", 500, "android", "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Medium.ttf"),
    FontCandidate("Roboto", 700, "android", "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Bold.ttf"),
    # Liberation Sans — metric-compatible substitute for Arial.
    FontCandidate("Liberation Sans", 400, "arial", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    FontCandidate("Liberation Sans", 700, "arial", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    # TeX Gyre Heros — GUST Font License (free, LPPL-equivalent, redistribution
    # explicitly permitted), built on URW Nimbus Sans L and purpose-designed
    # as a metric-compatible Helvetica substitute (unlike Inter above, which
    # is only an approximate visual stand-in) — see docs/fonts.md. Installed
    # via the `fonts-texgyre` Debian package (services/pipeline/Dockerfile).
    FontCandidate(
        "TeX Gyre Heros", 400, "helvetica", "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-regular.otf"
    ),
    FontCandidate(
        "TeX Gyre Heros", 700, "helvetica", "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-bold.otf"
    ),
    # Selawik — Microsoft's own official open-source (SIL OFL 1.1) font,
    # purpose-built as a metrics-compatible replacement for Segoe UI
    # (github.com/microsoft/Selawik) — replaces Noto Sans's previous role as
    # the "closest available, not a real metric match" Segoe UI stand-in
    # flagged in docs/fonts.md. Not packaged for Debian (only an old,
    # apparently-unfulfilled packaging request exists), so it's vendored
    # into the image directly from Microsoft's GitHub release rather than
    # via apt — see the Dockerfile.
    FontCandidate("Selawik", 400, "segoe_ui", "/usr/share/fonts/truetype/selawik/selawk.ttf"),
    FontCandidate("Selawik", 600, "segoe_ui", "/usr/share/fonts/truetype/selawik/selawksb.ttf"),
    FontCandidate("Selawik", 700, "segoe_ui", "/usr/share/fonts/truetype/selawik/selawkb.ttf"),
    # Noto Sans — wide script coverage fallback (general fallback for
    # coverage beyond Latin, though script support beyond Latin is out of
    # scope for v1 per the brief). No longer tagged as a Segoe UI stand-in
    # now that Selawik (above) fills that role with real metric compatibility.
    FontCandidate("Noto Sans", 400, "wide_coverage", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
    FontCandidate("Noto Sans", 700, "wide_coverage", "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
]


def _closest_candidate(family: str, weight: int) -> FontCandidate:
    """Exact (family, weight) match if registered, else the closest weight in that family."""
    exact = next((c for c in FONT_REGISTRY if c.family == family and c.weight == weight), None)
    if exact is not None:
        return exact

    same_family = [c for c in FONT_REGISTRY if c.family == family]
    if not same_family:
        raise ValueError(f"no registered font family named {family!r}")

    return min(same_family, key=lambda c: abs(c.weight - weight))


def find_font_path(family: str, weight: int) -> str:
    return _closest_candidate(family, weight).file_path


def style_role_for(family: str, weight: int) -> StyleRole:
    return _closest_candidate(family, weight).style_role


# Cap-height / unitsPerEm ratio for each substitute we actually render
# with — used only to convert a size *fitted against the substitute* into
# an estimate of what that text would be set at in the real platform font.
# Measured directly from each registry font file's own `OS/2.sCapHeight` /
# `head.unitsPerEm` (fontTools) — not a public-table guess — except "sf_pro"'s
# true-font counterpart below, which has no available real SF Pro file to
# measure and stays an approximation (flagged there, not here).
_CAP_HEIGHT_RATIO: dict[str, float] = {
    "Inter": 0.7275,
    "Roboto": 0.7109,
    "Liberation Sans": 0.6880,
    "Noto Sans": 0.7140,
    "TeX Gyre Heros": 0.7290,
    "Selawik": 0.7002,
}

# The real platform font's own cap-height ratio, keyed by style_role — only
# populated where there's a specific, well-founded true target.
# - "android" (Roboto is the real thing) and "arial" (Liberation Sans is a
#   metric-exact clone) are deliberately absent: their substitute is already
#   metric-accurate, so no correction applies.
# - "helvetica" reuses TeX Gyre Heros's own measured ratio above (0.729) as
#   the true-Helvetica value, rather than a separately-sourced number: TeX
#   Gyre Heros (built on URW Nimbus Sans L) is purpose-designed as a metric
#   clone of real Helvetica specifically, so its own measured cap-height
#   *is* the best available estimate of Helvetica's — this makes the
#   size-hint correction for TeX Gyre Heros matches a near-no-op by design,
#   not a bug to "fix" later.
# - "segoe_ui" is deliberately absent even though Selawik is metrics-
#   compatible with Segoe UI: that claim (per Microsoft's own docs) is about
#   glyph advance widths and line spacing, not cap-height specifically, and
#   there's no real Segoe UI file available here to verify a cap-height
#   match against — inventing a number would be exactly the kind of
#   overclaimed precision fonts.md's own substitution table avoids
#   elsewhere. `estimated_true_font_size` returns None for Selawik matches
#   until a verified figure exists.
# - "wide_coverage"/"sf_pro" are as before: no single true target font, or
#   no real font file available to measure against, respectively.
_TRUE_FONT_CAP_HEIGHT_RATIO: dict[StyleRole, float] = {
    "sf_pro": 0.714,  # approximation — no real SF Pro file available to measure
    "helvetica": 0.7290,  # = TeX Gyre Heros's own measured ratio, see above
}


def estimated_true_font_size(fitted_size: float, family: str, style_role: StyleRole) -> float | None:
    """Convert a size fitted against a substitute font into an estimate of
    what the same ink would be set at in the real platform font it stands
    in for. Display-only — never fed back into rendering, since /render
    always renders with the *substitute* file at its own fitted size (see
    stages/render_stage.py); feeding a "corrected" number back in would
    render the substitute at the wrong visual size.

    None when there's no well-documented true-font target for this
    candidate's role (see _TRUE_FONT_CAP_HEIGHT_RATIO).
    """
    substitute_ratio = _CAP_HEIGHT_RATIO.get(family)
    true_ratio = _TRUE_FONT_CAP_HEIGHT_RATIO.get(style_role)
    if substitute_ratio is None or true_ratio is None:
        return None
    return fitted_size * substitute_ratio / true_ratio
