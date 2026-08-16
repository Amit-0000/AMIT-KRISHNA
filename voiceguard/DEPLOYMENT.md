# Deployment Guide

This covers deploying the FastAPI backend + PostgreSQL + Redis + frontend stack beyond local
development. For local dev, see the main [README](README.md).

## Before you deploy anywhere real

`api/core/config.py`'s `validate_production()` runs at startup and **refuses to start** in
`APP_ENV=production` if any of the following still hold their local-dev defaults:

| Check | Fix |
|---|---|
| `JWT_SECRET` is still the dev default, or under 32 bytes | `openssl rand -hex 32`, set as `JWT_SECRET` |
| `AUDIT_IP_SALT` is still the dev default | `openssl rand -hex 32`, set as `AUDIT_IP_SALT` |
| `COOKIE_SECURE` is `false` | Set `true` — requires HTTPS in front of the app |
| `DEBUG` is `true` | Set `false` |
| `EMAIL_PROVIDER=smtp` but SMTP credentials are unset | Set `SMTP_HOST`/`SMTP_USERNAME`/`SMTP_PASSWORD`, or keep `EMAIL_PROVIDER=console` only for non-production |

This fail-fast check is intentional — treat a startup crash citing one of these as the app doing
its job, not a bug.

## Recommended path: Docker Compose behind a reverse proxy

1. Set `APP_ENV=production` and every value in the table above via your platform's secret
   management (not a committed `.env` file).
2. Put a TLS-terminating reverse proxy (nginx, Caddy, your cloud provider's load balancer) in
   front of the `backend` and `frontend` services. `docker-compose.yml`'s `backend` service binds
   `0.0.0.0:8000` with no TLS of its own by design (see `security_review.md`, finding F-09) — it
   is not meant to be exposed directly to the internet.
3. Set `ALLOWED_ORIGINS` to your real frontend origin(s) — the default
   (`http://localhost:5173,http://localhost:3000`) is dev-only.
4. `docker compose up --build -d` builds the backend from `api/Dockerfile.ml` and runs Alembic
   migrations automatically on container start (see the `CMD` in `api/Dockerfile.ml`).
5. Mount a persistent volume for `checkpoints/` (the model weights) and for uploaded scan storage
   (`UPLOAD_STORAGE_ROOT`, default `data/uploads`) if `STORAGE_BACKEND=local` — neither is baked
   into the image.

## Database

Migrations are managed with Alembic (`api/alembic/`). Run them explicitly rather than relying
only on the container's automatic `upgrade head` if you want migration application decoupled from
deployment:
```bash
alembic -c api/alembic.ini upgrade head    # run from voiceguard/
```
Size `DB_POOL_MAX_SIZE`/`REDIS_POOL_MAX_SIZE` for your expected concurrency — see
`performance/performance_fix_report.md` for the reasoning behind the current defaults (50/50,
sized for ~100 concurrent requests under the current bcrypt-offloaded auth path).

## Model checkpoint

The AI pipeline needs a checkpoint at `MODEL_CHECKPOINT_PATH` (default `checkpoints/best.pt`) to
serve real predictions — without one, `/predict` and the `/scans/*/process` pipeline return a
clean `503 Service Unavailable` rather than crashing (see `api/main.py`'s startup lifespan). See
[README → ML Models](README.md#ml-models) for how to produce or source a checkpoint. Every
checkpoint load in this codebase uses `torch.load(..., weights_only=True)` — verify any checkpoint
you deploy loads cleanly under that restriction before relying on it in production.

## Health checks

- `GET /health` — liveness, no auth required.
- The Docker container's own health depends on Postgres/Redis being reachable at startup
  (`init_engine`/`init_redis` in the lifespan hook); a container that never reaches "ready" is
  almost always a DB/Redis connectivity issue, not an application bug.

## Frontend (Vercel)

The `frontend/` app auto-deploys to production on every push to `main`, via Vercel's GitHub
integration (project root directory: `voiceguard/frontend`, since the repo is a monorepo).
`vercel.json` in that directory rewrites `/api/*` to the Railway backend — no frontend build-time
environment variables are required. To deploy manually instead (e.g. to bypass a broken CI run),
run `vercel deploy --prod` from `voiceguard/frontend`.

## What this repo does not include

- A CDN/object-storage backend for uploaded audio (`STORAGE_BACKEND` only supports `local` today
  — see [Roadmap](README.md#roadmap)).
- Autoscaling or multi-worker guidance beyond what's in `api/Dockerfile.ml`'s comments (the AI
  pipeline's model cache is a process-local in-memory dict — running multiple workers/replicas
  multiplies memory per instance rather than sharing a cache; each replica loads its own copy).
- A production secrets-management integration — bring your own (Vault, cloud secret manager,
  platform env-var injection, etc.).
