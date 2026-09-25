# paddle_v5_mobile and paddle_v5_server. Same PaddlePaddle/PaddleOCR pins as
# services/pipeline/bench/requirements-bench.txt. Models are baked in at build
# time; containers run with --network none.
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "numpy<2.0" \
    pillow==12.3.0 \
    opencv-contrib-python==4.10.0.84 \
    pyclipper==1.3.0.post6 \
    paddlepaddle==3.3.1 \
    paddleocr==3.7.0 \
    setuptools

COPY scripts/engines/base.py scripts/engines/paddle_engine.py /build/
RUN cd /build && python -c "import paddle_engine as p; p.bake()"

WORKDIR /bench
