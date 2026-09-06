FROM python:3.12-slim

WORKDIR /bench

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libegl1 \
    libglib2.0-0 \
    libgomp1 \
    fonts-inter \
    fonts-roboto \
    fonts-liberation \
    fonts-noto-core \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-bench.txt .
RUN pip install --no-cache-dir -r requirements-bench.txt

# Bake every engine's models in at build time, same rationale as the
# production Dockerfile: no request should pay a cold CDN download.
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(text_detection_model_name='PP-OCRv5_mobile_det', text_recognition_model_name='PP-OCRv5_mobile_rec', use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False, enable_mkldnn=False)"

# RapidOCR arms both run the exact PP-OCRv5 mobile 'ch' det/rec ONNX export
# (same file for the onnxruntime and openvino engine_types — RapidOCR's own
# default_models.yaml lists identical SHA256 for both), so this isolates
# inference-runtime (ONNX Runtime vs OpenVINO) rather than comparing
# different models. Baking both engine_types here downloads the shared
# .onnx files once.
RUN python -c "\
from rapidocr import RapidOCR; \
from rapidocr.utils.typings import EngineType, ModelType, OCRVersion, LangDet, LangRec; \
[RapidOCR(params={ \
    'Det.engine_type': engine, 'Det.ocr_version': OCRVersion.PPOCRV5, 'Det.model_type': ModelType.MOBILE, 'Det.lang_type': LangDet.CH, \
    'Rec.engine_type': engine, 'Rec.ocr_version': OCRVersion.PPOCRV5, 'Rec.model_type': ModelType.MOBILE, 'Rec.lang_type': LangRec.CH, \
    'Global.use_cls': False, \
}) for engine in (EngineType.ONNXRUNTIME, EngineType.OPENVINO)] \
"

COPY . .

CMD ["python", "run_benchmark.py"]
