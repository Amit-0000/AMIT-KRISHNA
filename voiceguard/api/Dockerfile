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

# Run the actual server as a non-root user (security-review.md F-25) —
# narrows the blast radius of any future code-execution vulnerability in the
# app or a dependency. The image itself still starts as root (no USER line
# here): docker-entrypoint.sh needs root to fix ownership on docker-compose's
# ./data/uploads bind mount (which keeps whatever host-side UID created
# it — root, on a fresh checkout/CI runner where Docker auto-creates it) at
# *container start*, before dropping to appuser for the real process — a
# build-time-only `chown` (as this image used to rely on) can't reach a
# bind mount layered on top at run time. See docker-entrypoint.sh's comment
# for the real PermissionError this replaces.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data/uploads \
    && chown -R appuser:appuser /app
COPY api/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["alembic -c api/alembic.ini upgrade head && uvicorn api.main:app --host 0.0.0.0 --port 8000"]
