FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libegl1 \
    libglib2.0-0 \
    libgomp1 \
    fonts-inter \
    fonts-roboto \
    fonts-liberation \
    fonts-noto-core \
    fonts-texgyre \
    unzip \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Selawik (Microsoft's official open-source, SIL OFL 1.1, metrics-compatible
# Segoe UI substitute — github.com/microsoft/Selawik) isn't packaged for
# Debian, so it's vendored directly from its one pinned GitHub release
# rather than apt-get. `unzip`/`ca-certificates`/`curl` above exist only to
# support this step; consider dropping them if this vendoring approach is
# replaced.
RUN mkdir -p /usr/share/fonts/truetype/selawik \
    && curl -fL -o /tmp/selawik.zip https://github.com/microsoft/Selawik/releases/download/1.01/Selawik_Release.zip \
    && unzip -j /tmp/selawik.zip 'selawk.ttf' 'selawksb.ttf' 'selawkb.ttf' -d /usr/share/fonts/truetype/selawik \
    && rm /tmp/selawik.zip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# PaddleOCR otherwise fetches its det/rec/cls model files from its CDN the
# first time get_ocr_engine() runs — a ~70s stall inside whatever request
# happens to be unlucky enough to trigger it, with no way for that request
# to report progress on a plain network download. Baking the models into
# the image at build time means every container starts warm, with no
# runtime dependency on the CDN or on the paddleocr-models volume surviving.
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(text_detection_model_name='PP-OCRv5_mobile_det', text_recognition_model_name='PP-OCRv5_mobile_rec', use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False, enable_mkldnn=False)"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
