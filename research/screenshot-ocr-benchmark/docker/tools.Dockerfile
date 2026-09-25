# Rendering, variant generation, scoring and validation.
# Playwright's official image pins Chromium to the Playwright release.
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

RUN pip install --no-cache-dir \
    playwright==1.63.0 \
    pillow==12.3.0 \
    numpy==2.3.4 \
    scikit-image==0.26.0 \
    fonttools[woff]==4.60.1 \
    rapidfuzz==3.14.1 \
    pyarrow==21.0.0 \
    pytest==8.4.2

WORKDIR /bench
