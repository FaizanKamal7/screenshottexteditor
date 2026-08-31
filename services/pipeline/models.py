from typing import Literal

from pydantic import BaseModel


class CharBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class GradientStop(BaseModel):
    position: float  # 0..1 along the gradient axis
    color: tuple[int, int, int]


class BackgroundFill(BaseModel):
    kind: Literal["flat", "gradient"]
    color: tuple[int, int, int] | None = None
    angle_deg: float | None = None
    stops: list[GradientStop] = []


class UiElement(BaseModel):
    kind: Literal["button", "pill", "input", "unknown"] = "unknown"
    bbox: tuple[float, float, float, float]
    fill_color: tuple[int, int, int]


class FontCandidateScore(BaseModel):
    family: str
    weight: int
    score: float


class Region(BaseModel):
    id: str
    text: str
    bbox: tuple[float, float, float, float]
    block_id: str
    chars: list[CharBox] = []
    script: Literal["latin"] = "latin"
    direction: Literal["ltr", "rtl"] = "ltr"
    confidence: float | None = None
    alpha_mask_png: str | None = None

    font_family: str | None = None
    font_weight: int | None = None
    font_size: float | None = None
    letter_spacing: float = 0.0
    baseline_y: float | None = None
    text_color: tuple[int, int, int] | None = None
    background: BackgroundFill | None = None
    alignment: Literal["left", "center", "right"] = "left"
    line_height: float | None = None
    ui_element: UiElement | None = None
    font_candidates: list[FontCandidateScore] = []


class AnalyzeResponse(BaseModel):
    image_width: int
    image_height: int
    scale_factor: Literal[1, 2, 3]
    regions: list[Region]
