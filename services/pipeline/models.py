from typing import Literal

from pydantic import BaseModel


class Region(BaseModel):
    id: str
    text: str
    bbox: tuple[float, float, float, float]
    block_id: str
    script: Literal["latin"] = "latin"
    direction: Literal["ltr", "rtl"] = "ltr"
    confidence: float | None = None


class AnalyzeResponse(BaseModel):
    image_width: int
    image_height: int
    regions: list[Region]
