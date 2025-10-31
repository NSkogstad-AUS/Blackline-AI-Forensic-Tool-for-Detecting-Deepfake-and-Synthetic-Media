# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_ROOT=/app/backend/data \
    MODELS_DIR=/app/backend/models \
    STORAGE_BACKEND=local

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG BACKEND_REQUIREMENTS=backend/requirements-lite.txt
COPY ${BACKEND_REQUIREMENTS} /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r /tmp/requirements.txt

# Copy backend application code
COPY backend/src /app/backend/src
COPY backend/models /app/backend/models
COPY backend/tests /app/backend/tests
COPY backend/*.py /app/backend/

# Provide a writable data root inside the image for quick smoke tests
RUN mkdir -p /app/backend/data/raw /app/backend/data/uploads /app/backend/data/derived

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.src.api_server:app --host 0.0.0.0 --port ${PORT:-8000}"]
