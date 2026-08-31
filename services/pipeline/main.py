import io
import os
import uuid

from fastapi import FastAPI, Header, HTTPException, UploadFile, status
from PIL import Image

from models import AnalyzeResponse, Region

app = FastAPI(title="screenshottexteditor pipeline")

PIPELINE_SHARED_SECRET = os.environ.get("PIPELINE_SHARED_SECRET", "")


def require_shared_secret(x_pipeline_secret: str | None) -> None:
    if not PIPELINE_SHARED_SECRET or x_pipeline_secret != PIPELINE_SHARED_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile,
    x_pipeline_secret: str | None = Header(default=None, alias="X-Pipeline-Secret"),
) -> AnalyzeResponse:
    require_shared_secret(x_pipeline_secret)

    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    width, height = image.size

    block_id = str(uuid.uuid4())
    stub_regions = [
        Region(
            id=str(uuid.uuid4()),
            text="Sample Heading",
            bbox=(width * 0.08, height * 0.08, width * 0.5, height * 0.06),
            block_id=block_id,
            confidence=None,
        ),
        Region(
            id=str(uuid.uuid4()),
            text="Sample subtitle text goes here",
            bbox=(width * 0.08, height * 0.18, width * 0.6, height * 0.04),
            block_id=block_id,
            confidence=None,
        ),
        Region(
            id=str(uuid.uuid4()),
            text="Continue",
            bbox=(width * 0.08, height * 0.85, width * 0.3, height * 0.07),
            block_id=str(uuid.uuid4()),
            confidence=None,
        ),
    ]

    return AnalyzeResponse(image_width=width, image_height=height, regions=stub_regions)
