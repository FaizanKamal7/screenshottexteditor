# easyocr and doctr (both PyTorch, CPU-only wheels). Models baked at build time.
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
    torch==2.8.0 torchvision==0.23.0
RUN pip install --no-cache-dir \
    pillow==12.3.0 \
    easyocr==1.7.2 \
    python-doctr==1.1.0

COPY scripts/engines/base.py scripts/engines/torch_engines.py /build/
RUN cd /build && python -c "import torch_engines as t; t.bake()"

WORKDIR /bench
