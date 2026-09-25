# tesseract5: Debian bookworm's Tesseract 5 package, with the eng model from
# tessdata_best pinned by commit (not the distro's default tessdata).
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG TESSDATA_BEST_COMMIT=e12c65a915945e4c28e237a9b52bc4a8f39a0cec
RUN mkdir -p /opt/tessdata_best \
    && curl -fsSL -o /opt/tessdata_best/eng.traineddata \
       "https://github.com/tesseract-ocr/tessdata_best/raw/${TESSDATA_BEST_COMMIT}/eng.traineddata" \
    && cp /usr/share/tesseract-ocr/5/tessdata/osd.traineddata /opt/tessdata_best/ 2>/dev/null || true \
    && echo "${TESSDATA_BEST_COMMIT}" > /opt/tessdata_best/COMMIT
ENV TESSDATA_PREFIX=/opt/tessdata_best

RUN pip install --no-cache-dir pillow==12.3.0 numpy==2.3.4 pytesseract==0.3.13

WORKDIR /bench
