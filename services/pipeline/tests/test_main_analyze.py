import io
import json
import os

os.environ.setdefault("PIPELINE_SHARED_SECRET", "test-secret")

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from main import app
from ocr_engine import RawLine

client = TestClient(app)
SECRET = os.environ["PIPELINE_SHARED_SECRET"]


class _FakeOcrEngine:
    """Stands in for PaddleOCR, which isn't installed in this environment.

    Returns fixed lines matching what `_multi_line_png_bytes` actually draws,
    so the streaming/progress logic downstream of detect() gets exercised
    against real per-line pixel work (separate/match/color/ui-element), not
    just mocked data all the way through.
    """

    def run(self, image_bgr):  # noqa: ARG002 - matches OcrEngine.run's signature
        return [
            RawLine(quad=[(10, 8), (110, 8), (110, 28), (10, 28)], text="Hello world", confidence=0.95),
            RawLine(quad=[(10, 38), (110, 38), (110, 58), (10, 58)], text="Second line", confidence=0.95),
            RawLine(quad=[(10, 68), (110, 68), (110, 88), (10, 88)], text="Third line", confidence=0.95),
        ]


def _sample_png_bytes() -> bytes:
    image = Image.new("RGB", (200, 60), color=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _multi_line_png_bytes() -> bytes:
    image = Image.new("RGB", (200, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.text((10, 10), "Hello world", fill=(0, 0, 0))
    draw.text((10, 40), "Second line", fill=(0, 0, 0))
    draw.text((10, 70), "Third line", fill=(0, 0, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _parse_ndjson(body: bytes) -> list[dict]:
    lines = [line for line in body.decode("utf-8").split("\n") if line.strip()]
    return [json.loads(line) for line in lines]


def test_analyze_requires_shared_secret():
    files = {"file": ("test.png", _sample_png_bytes(), "image/png")}

    response = client.post("/analyze", files=files)

    assert response.status_code == 401


def test_analyze_streams_ndjson_progress_then_result(monkeypatch):
    monkeypatch.setattr("stages.detect.get_ocr_engine", lambda: _FakeOcrEngine())

    files = {"file": ("test.png", _multi_line_png_bytes(), "image/png")}

    response = client.post("/analyze", files=files, headers={"X-Pipeline-Secret": SECRET})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")

    messages = _parse_ndjson(response.content)
    assert len(messages) >= 2

    progress_messages = [m for m in messages if m["type"] == "progress"]
    result_messages = [m for m in messages if m["type"] == "result"]

    assert len(result_messages) == 1
    assert len(progress_messages) >= 1

    # current climbs monotonically to total, and every progress message
    # agrees on the same total (set once, from the initial detect() pass).
    total = progress_messages[0]["total"]
    for i, message in enumerate(progress_messages):
        assert message["total"] == total
        assert message["current"] == i

    result = result_messages[0]
    assert "regions" in result
    assert isinstance(result["regions"], list)
    assert "image_width" in result and "image_height" in result and "scale_factor" in result
