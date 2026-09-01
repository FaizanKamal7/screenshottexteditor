import base64
import io
import json
import os

os.environ.setdefault("PIPELINE_SHARED_SECRET", "test-secret")

from fastapi.testclient import TestClient
from PIL import Image

from main import app

client = TestClient(app)
SECRET = os.environ["PIPELINE_SHARED_SECRET"]


def _sample_png_bytes() -> bytes:
    image = Image.new("RGB", (200, 60), color=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_render_requires_shared_secret():
    files = {"file": ("test.png", _sample_png_bytes(), "image/png")}

    response = client.post("/render", files=files, data={"edits": "[]"})

    assert response.status_code == 401


def test_render_rejects_invalid_edits_payload():
    files = {"file": ("test.png", _sample_png_bytes(), "image/png")}

    response = client.post(
        "/render", files=files, data={"edits": "not json"}, headers={"X-Pipeline-Secret": SECRET}
    )

    assert response.status_code == 400


def test_render_returns_png_and_per_region_results():
    files = {"file": ("test.png", _sample_png_bytes(), "image/png")}
    edits = [
        {
            "region_id": "r1",
            "bbox": [20.0, 15.0, 100.0, 24.0],
            "text": "Goodbye",
            "font_family": "Inter",
            "font_weight": 400,
            "font_size": 18.0,
            "letter_spacing": 0.0,
            "baseline_y": 33.0,
            "text_color": [20, 20, 20],
            "background": {"kind": "flat", "color": [255, 255, 255], "angle_deg": None, "stops": []},
            "alignment": "left",
        }
    ]

    response = client.post(
        "/render", files=files, data={"edits": json.dumps(edits)}, headers={"X-Pipeline-Secret": SECRET}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["region_id"] == "r1"
    assert body["results"][0]["overflowed"] is False

    decoded = base64.b64decode(body["image_png_base64"])
    out_image = Image.open(io.BytesIO(decoded))
    assert out_image.size == (200, 60)


def test_render_rejects_unknown_font_family():
    files = {"file": ("test.png", _sample_png_bytes(), "image/png")}
    edits = [
        {
            "region_id": "r1",
            "bbox": [20.0, 15.0, 100.0, 24.0],
            "text": "Goodbye",
            "font_family": "Comic Sans MS",
            "font_weight": 400,
            "font_size": 18.0,
            "letter_spacing": 0.0,
            "baseline_y": 33.0,
            "text_color": [20, 20, 20],
            "background": None,
            "alignment": "left",
        }
    ]

    response = client.post(
        "/render", files=files, data={"edits": json.dumps(edits)}, headers={"X-Pipeline-Secret": SECRET}
    )

    assert response.status_code == 400
