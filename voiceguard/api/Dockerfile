# ──────────────────────────────────────────────────────────────────────────────
# VoiceGuard backend — auth/user platform (Product Foundation slice)
#
# Deliberately lean: only api/requirements.txt is installed here (FastAPI,
# SQLAlchemy, Alembic, JWT, bcrypt, Redis client — no torch/librosa/gradio).
# main.py lazy-imports the ML inference code, so /predict returns a clean 503
# in this image instead of failing to boot; build the root Dockerfile instead
# if you need a container that actually serves predictions.
#
# Build (from the voiceguard/ repo root, not from api/):
#   docker build -f api/Dockerfile -t voiceguard-backend .
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY api/ api/
# src/ is imported lazily by api/main.py for /predict; included so that path
# resolves for deployments that DO mount a checkpoint, without requiring torch
# to be installed for auth-only usage (the import itself is guarded).
COPY src/ src/

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8000

CMD ["sh", "-c", "alembic -c api/alembic.ini upgrade head && uvicorn api.main:app --host 0.0.0.0 --port 8000"]
