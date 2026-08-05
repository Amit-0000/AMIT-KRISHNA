from __future__ import annotations

import sys
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Application ──────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_BASE_URL: str = "http://localhost:5173"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024
    MAX_AUDIO_DURATION_S: int = 300

    # Secure cookies require HTTPS. The architecture spec (BATCH_04 S10.2) mandates
    # Secure:true unconditionally, but that makes cookie-based auth undeliverable over
    # plain http://localhost during local development. COOKIE_SECURE lets dev relax this
    # exactly the way BATCH_04 S15.3 sanctions relaxing other production defaults; it must
    # be true in staging/production (enforced in validate_production below).
    COOKIE_SECURE: bool = False

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://voiceguard:voiceguard@localhost:5432/voiceguard"
    # Sized for a single uvicorn worker under ~100 concurrent requests: every
    # write path (login, scan create/cancel/delete, ...) opens a second,
    # short-lived connection for its own audit-log session (see
    # api.core.audit.write_audit_log's docstring for why that's a separate
    # session rather than reusing the request's), so peak concurrent
    # connections can run well above the request concurrency itself. The
    # previous default (5 base + 15 overflow = 20) was sized for the
    # pre-fix world where a blocking bcrypt call on the event loop serialized
    # nearly all request handling and connections were rarely contended;
    # once that block was removed (see api.core.security.verify_password),
    # 100 concurrent VUs started exhausting a 20-connection pool outright
    # (sqlalchemy.exc.TimeoutError: QueuePool limit ... reached — see
    # performance/performance_fix_report.md Phase 4). 50 total connections
    # stays well inside Postgres's default max_connections=100 with room for
    # migrations/admin/seed tooling alongside the app.
    DB_POOL_MIN_SIZE: int = 10
    DB_POOL_MAX_SIZE: int = 50
    DB_STATEMENT_TIMEOUT_S: int = 30
    DB_CONNECT_TIMEOUT_S: int = 5

    # ── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    # Same reasoning as DB_POOL_MAX_SIZE above: 10 connections was enough
    # while a blocking bcrypt call kept request handling effectively
    # serialized, but once that block was removed, ~100 concurrent
    # rate-limited requests (login, scan create) started hitting
    # redis.exceptions.ConnectionError: Too many connections against this
    # client-side pool cap — Redis server itself defaults to maxclients=10000,
    # so this was purely an underprovisioned client pool, not a Redis limit.
    REDIS_POOL_MAX_SIZE: int = 50
    REDIS_COMMAND_TIMEOUT_S: float = 1.0

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET: str = "dev-only-insecure-secret-change-me-before-deploying-anywhere-real"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_TTL_S: int = 900
    JWT_REFRESH_TOKEN_TTL_S: int = 2592000

    # ── Email ────────────────────────────────────────────────────────────────
    EMAIL_PROVIDER: Literal["console", "smtp"] = "console"
    EMAIL_FROM_ADDRESS: str = "no-reply@voiceguard.app"
    EMAIL_FROM_NAME: str = "VoiceGuard"
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_TLS: bool = True

    # ── Rate limiting (auth routes; scan/API-key tiers belong to later slices) ─
    RATE_LIMIT_LOGIN_PER_HOUR_PER_IP: int = 10
    RATE_LIMIT_REGISTER_PER_HOUR_PER_IP: int = 5
    RATE_LIMIT_RESET_PER_HOUR_PER_IP: int = 3
    RATE_LIMIT_RESEND_VERIFICATION_PER_HOUR_PER_IP: int = 3
    RATE_LIMIT_VERIFY_EMAIL_PER_HOUR_PER_IP: int = 10
    RATE_LIMIT_SCAN_CREATE_PER_HOUR_PER_USER: int = 30
    # /predict is the legacy top-level inference endpoint (pre-dates the
    # /scans pipeline) — kept alongside the scan-create limit for parity,
    # since it's just as CPU-bound (see security_review.md F-03/F-04).
    RATE_LIMIT_PREDICT_PER_HOUR_PER_USER: int = 30

    # ── Audit ────────────────────────────────────────────────────────────────
    AUDIT_IP_SALT: str = "dev-only-audit-ip-salt-change-me"

    # ── Sharing (public read-only scan result links) ────────────────────────
    SHARE_TOKEN_EXPIRY_DAYS: int = 30

    # ── Scan upload & storage (Audio Upload & Scan Management slice) ──────────
    # MAX_UPLOAD_SIZE_BYTES / MAX_AUDIO_DURATION_S predate this slice (see the
    # Application block above) and are reused as-is rather than duplicated.
    MIN_UPLOAD_SIZE_BYTES: int = 1024
    STORAGE_BACKEND: Literal["local"] = "local"
    UPLOAD_STORAGE_ROOT: str = "data/uploads"
    SCAN_EXPIRY_HOURS: int = 24
    PREPROCESSING_MAX_ATTEMPTS: int = 3

    # ── AI Processing Pipeline & Detection Engine (Slice 03) ───────────────────
    # Read from an env var with an explicit default rather than the bare
    # relative "checkpoints/best.pt" api/main.py's legacy /predict uses — see
    # Vulnerability Test Results/security_review.md F-13. Resolved to an
    # absolute path once in api.inference.model_registry so a process started
    # from an unexpected working directory fails fast and clearly instead of
    # silently missing the checkpoint.
    MODEL_CHECKPOINT_PATH: str = "checkpoints/best.pt"
    MODEL_NAME: str = "lcnn"
    MODEL_VERSION: str = "v1"
    MODEL_DEVICE: Literal["auto", "cpu", "cuda", "mps"] = "auto"
    # Second supported architecture (AudioCNN — see api.inference.adapters).
    # Unlike MODEL_CHECKPOINT_PATH/MODEL_NAME/MODEL_VERSION above, nothing
    # auto-registers this on startup — registering and activating it is a
    # deliberate, explicit call to api.inference.model_registry.register_model_version
    # / switch_active_model (see that module), not something every process
    # boot does unprompted. This setting only supplies *where* the checkpoint
    # would be found if and when an operator chooses to register it.
    AUDIO_CNN_CHECKPOINT_PATH: str = "checkpoints/deepfake_cnn.pth"
    # Bounded, whole-stage retry (mirrors PREPROCESSING_MAX_ATTEMPTS) — a
    # single AI_PIPELINE_STAGES stage is retried this many times before the
    # job gives up and lands the scan in that stage's *_FAILED terminal state.
    AI_STAGE_MAX_ATTEMPTS: int = 3
    AI_STAGE_TIMEOUT_S: float = 30.0
    # Below this softmax score the verdict is reported as "uncertain" rather
    # than forcing a bonafide/spoof call (Threshold Decision / Confidence
    # Calibration — see api.inference.confidence).
    AI_CONFIDENCE_THRESHOLD: float = 0.60
    AI_MIN_AUDIO_DURATION_S: float = 0.5
    # RMS amplitude below this (on a [-1, 1] normalized waveform) is treated
    # as silence for trimming/detection purposes.
    AI_SILENCE_RMS_THRESHOLD: float = 0.01
    FEATURE_EXTRACTOR_NAME: str = "logmel"
    FEATURE_EXTRACTOR_VERSION: str = "v1"
    # Persisting full feature arrays is a debugging/reproducibility aid, not a
    # correctness requirement — large deployments may disable it to save
    # storage without changing pipeline behavior.
    FEATURE_VECTOR_STORAGE_ENABLED: bool = True

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def _non_empty_origins(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ALLOWED_ORIGINS must not be empty")
        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    def validate_production(self) -> None:
        """Fail fast on startup rather than silently running with insecure
        defaults in a real deployment (BATCH_04 S15.4)."""
        errors: list[str] = []
        if self.is_production:
            if self.JWT_SECRET == Settings.model_fields["JWT_SECRET"].default:
                errors.append("JWT_SECRET must be set to a unique 256-bit+ secret in production")
            if len(self.JWT_SECRET.encode()) < 32:
                errors.append("JWT_SECRET must be at least 32 bytes")
            if not self.COOKIE_SECURE:
                errors.append("COOKIE_SECURE must be true in production")
            if self.DEBUG:
                errors.append("DEBUG must be false in production")
            if self.AUDIT_IP_SALT == Settings.model_fields["AUDIT_IP_SALT"].default:
                errors.append("AUDIT_IP_SALT must be set to a unique value in production")
            if self.EMAIL_PROVIDER == "smtp" and not all(
                [self.SMTP_HOST, self.SMTP_USERNAME, self.SMTP_PASSWORD]
            ):
                errors.append("SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD are required when EMAIL_PROVIDER=smtp")
        if errors:
            print("FATAL: invalid configuration for APP_ENV=production:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            raise SystemExit(1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
