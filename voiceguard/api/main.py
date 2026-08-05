import logging
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.auth.router import router as auth_router
from api.core.audio_formats import ALLOWED_AUDIO_EXTENSIONS
from api.core.config import get_settings
from api.core.database import dispose_engine, init_engine
from api.core.deps import require_authenticated
from api.core.exceptions import InvalidInputError, ServiceUnavailableError, register_exception_handlers
from api.core.middleware import RequestContextMiddleware
from api.core.rate_limit import require_predict_rate_limit
from api.core.redis import close_redis, init_redis
from api.core.responses import success_envelope
from api.dashboard.router import router as dashboard_router
from api.feedback.router import router as feedback_router
from api.inference.router import models_router
from api.inference.router import router as inference_router
from api.notifications.router import router as notifications_router
from api.scans.jobs import expire_stale_scans_on_startup
from api.scans.router import router as scans_router
from api.schemas import PredictionResponse
from api.sharing.router import router as sharing_router
from api.user.models import User
from api.user.router import router as user_router

logger = logging.getLogger("voiceguard")

CHECKPOINT = Path("checkpoints/best.pt")


def _get_device():
    import torch

    if torch.cuda.is_available():
        return torch.device("cuda")
    elif torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate_production()

    logging.basicConfig(level=settings.LOG_LEVEL)

    init_engine(settings.DATABASE_URL)
    init_redis(settings.REDIS_URL)

    # No scheduler (Celery beat / cron) exists yet to run this periodically —
    # see the design doc's Concurrency/Background Processing notes — so a
    # startup sweep is the pragmatic stopgap that reaps anything that expired
    # while the process was down, without adding new infra for this slice.
    await expire_stale_scans_on_startup()

    # ML model load is best-effort at startup: the Product Foundation slice
    # (auth/user) must come up even on a machine with no trained checkpoint or
    # no torch/librosa install. /predict reports 503 until a model is loaded.
    app.state.model = None
    app.state.device = None
    try:
        from src.inference.predict import load_model

        device = _get_device()
        app.state.device = device
        app.state.model = load_model(CHECKPOINT, device)
        logger.info("ML model loaded on %s", device)
    except Exception as exc:  # noqa: BLE001 - startup must not crash on a missing/broken checkpoint
        logger.warning("ML model not loaded (%s: %s) — /predict will return 503 until available", type(exc).__name__, exc)

    yield

    await dispose_engine()
    await close_redis()


app = FastAPI(
    title="VoiceGuard API",
    description="VoiceGuard backend: authentication, user platform, scan management, and the AI processing pipeline.",
    version="0.3.0",
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Guest-Token", "X-Request-ID"],
)

register_exception_handlers(app)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(scans_router, prefix="/api/v1")
app.include_router(inference_router, prefix="/api/v1")
app.include_router(models_router, prefix="/api/v1")
app.include_router(sharing_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")


@app.get("/health")
def health():
    return success_envelope({"status": "ok"})


@app.post("/predict", response_model=None, dependencies=[Depends(require_predict_rate_limit)])
async def predict_endpoint(audio_file: UploadFile = File(...), user: User = Depends(require_authenticated)):
    if app.state.model is None:
        raise ServiceUnavailableError("The detection model is not loaded on this deployment yet.")

    contents = await audio_file.read()
    if len(contents) > get_settings().MAX_UPLOAD_SIZE_BYTES:
        raise InvalidInputError("File too large. Max 10MB.")

    suffix = Path(audio_file.filename or "").suffix.lower()
    if suffix not in ALLOWED_AUDIO_EXTENSIONS:
        raise InvalidInputError("Unsupported format. Use wav, flac, mp3, m4a, ogg, or aiff.")

    from src.inference.predict import predict

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        result = predict(tmp_path, app.state.model, app.state.device)
    finally:
        tmp_path.unlink(missing_ok=True)

    return PredictionResponse(**result)
