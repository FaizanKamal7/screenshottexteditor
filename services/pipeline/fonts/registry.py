from dataclasses import dataclass
from typing import Literal

# Which real, licensed platform font each candidate stands in for.
# Purely informational (docs/UI labeling) — never used by the matcher itself.
StyleRole = Literal["sf_pro", "helvetica", "android", "arial", "wide_coverage"]


@dataclass(frozen=True)
class FontCandidate:
    family: str
    weight: int
    style_role: StyleRole
    file_path: str


FONT_REGISTRY: list[FontCandidate] = [
    # Inter — substitute for SF Pro (iOS/macOS) and Helvetica.
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
    # Noto Sans — wide script coverage fallback; also the closest open
    # stand-in available for Windows' Segoe UI (no true open metric clone
    # of Segoe UI exists — flagged honestly in docs/fonts.md).
    FontCandidate("Noto Sans", 400, "wide_coverage", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
    FontCandidate("Noto Sans", 700, "wide_coverage", "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
]


def find_font_path(family: str, weight: int) -> str:
    """Exact (family, weight) match if registered, else the closest weight in that family."""
    exact = next((c for c in FONT_REGISTRY if c.family == family and c.weight == weight), None)
    if exact is not None:
        return exact.file_path

    same_family = [c for c in FONT_REGISTRY if c.family == family]
    if not same_family:
        raise ValueError(f"no registered font family named {family!r}")

    closest = min(same_family, key=lambda c: abs(c.weight - weight))
    return closest.file_path
