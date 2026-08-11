# ──────────────────────────────────────────────────────────────────────────────
# VoiceGuard backend — ML-enabled runtime
#
# Same api.main:app as api/Dockerfile (auth/user/scans/inference/sharing/
# notifications/feedback/dashboard — every router, unchanged), plus the ML
# runtime api/inference/model_loader.py needs to actually load a registered
# model instead of returning MODEL_NOT_AVAILABLE. Nothing about the pipeline,
# the model registry, or the adapter interface is different here — this
# image only changes what's installed.
#
# api/requirements-ml.txt is a deliberately narrow slice of the root
# requirements.txt: torch/torchaudio/soundfile/numpy/pydub/librosa/pandas,
# the exact set api/inference/* and the vendored src/models/audio_cnn.py +
# src/data/dataset.py import — not gradio/scipy/scikit-learn/matplotlib/
# huggingface_hub, which the serving path never touches for the currently
# -registered AudioCNN model.
#
# Checkpoint is still mounted at runtime, not baked in (see docker-compose.yml
# ./checkpoints:/app/checkpoints:ro) — this image is reusable across
# different trained checkpoints, same as api/Dockerfile.
#
# Build (from the voiceguard/ repo root, not from api/):
#   docker build -f api/Dockerfile.ml -t voiceguard-backend-ml .
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

# ffmpeg: src.data.dataset.load_waveform's pydub fallback (mp3/m4a formats
# soundfile can't read directly) shells out to it — same reason the root
# Dockerfile installs it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY api/requirements-ml.txt api/requirements-ml.txt
RUN pip install --no-cache-dir -r api/requirements-ml.txt

COPY api/ api/
COPY src/ src/

# Run as a non-root user (security-review.md F-25) — see api/Dockerfile's
# identical comment for the bind-mount ownership caveat on Linux hosts.
# checkpoints/ stays read-only (mounted :ro in docker-compose.yml) so this
# user only ever needs write access under data/uploads/.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data/uploads /app/checkpoints \
    && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8000

# --workers 1: model_loader._MODEL_CACHE is an in-process dict — multiple
# workers would each load their own copy, multiplying RAM for no benefit
# (same reasoning as the root Dockerfile's own --workers 1). The concurrency
# bottleneck this caused under load (security-review.md F-17) was addressed
# via DB_POOL_MIN_SIZE/DB_POOL_MAX_SIZE instead (api/core/config.py) — a
# single async worker can serve far more than 100 concurrent I/O-bound
# requests once it isn't starved for DB connections; raising --workers here
# would trade that fixed problem for multiplying the ML model's RAM
# footprint per worker for no throughput benefit on I/O-bound endpoints.
CMD ["sh", "-c", "alembic -c api/alembic.ini upgrade head && uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1"]
