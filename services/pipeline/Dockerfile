# Pinned to the exact digest of the last known-good build (2026-09-01) rather
# than floating python:3.12-slim: an unpinned tag re-resolves to whatever
# Debian ships on every rebuild, and a later point-release drift is the
# leading suspect for a paddlepaddle C++ segfault inside zlib's
# inflateReset2 that reproduced on two builds against today's :slim tag but
# never happened on this digest.
FROM python:3.12-slim@sha256:e5c9fa26ffb76e11e0f054f30dc2523a2f9693f0c36c0cf1e39b27e152d899fc

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
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# PaddleOCR otherwise fetches its det/rec/cls model files from its CDN the
# first time get_ocr_engine() runs — a ~70s stall inside whatever request
# happens to be unlucky enough to trigger it, with no way for that request
# to report progress on a plain network download. Baking the models into
# the image at build time means every container starts warm, with no
# runtime dependency on the CDN or on the paddleocr-models volume surviving.
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=False, lang='en', show_log=False)"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
