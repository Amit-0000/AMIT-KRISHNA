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

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8000

# --workers 1: model_loader._MODEL_CACHE is an in-process dict — multiple
# workers would each load their own copy, multiplying RAM for no benefit
# (same reasoning as the root Dockerfile's own --workers 1).
CMD ["sh", "-c", "alembic -c api/alembic.ini upgrade head && uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1"]
