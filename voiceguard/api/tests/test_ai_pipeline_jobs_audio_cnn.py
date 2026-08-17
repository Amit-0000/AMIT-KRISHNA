from __future__ import annotations

import io
import struct
import uuid
import wave
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.inference import jobs as jobs_module
from api.inference import model_registry
from api.inference import repository as inference_repository
from api.inference import service as inference_service
from api.inference.models import FeatureVector, ProcessingFailure, ProcessingMetric
from api.scans import repository as scans_repository
from api.scans.models import ScanEvent
from api.scans.state_machine import ScanStatus

pytestmark = pytest.mark.asyncio


def _wav_bytes(seconds: float = 1.0, rate: int = 16000, tone: int = 2500) -> bytes:
    n_frames = int(seconds * rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack("<" + "h" * n_frames, *([tone] * n_frames)))
    return buf.getvalue()


def _extract_token(url: str) -> str:
    return parse_qs(urlparse(url).query)["token"][0]


@pytest.fixture
def captured_emails(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    from api.core import email as email_service

    captured: dict[str, str] = {}

    async def fake_verification_email(*, to: str, verification_url: str) -> None:
        captured["verification_url"] = verification_url

    monkeypatch.setattr(email_service, "send_verification_email", fake_verification_email)
    return captured


async def _register_verify_login(client: AsyncClient, captured_emails: dict[str, str], *, email: str) -> None:
    resp = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "Str0ng!Pass", "display_name": "Tester"}
    )
    assert resp.status_code == 201, resp.text
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass"})
    assert login.status_code == 200, login.text


async def _upload_and_reach_ready_for_ai(client: AsyncClient, db_session: AsyncSession, *, tone: int = 2500) -> str:
    from api.scans import jobs as scans_jobs_module

    resp = await client.post(
        "/api/v1/scans", files={"file": ("clip.wav", _wav_bytes(tone=tone), "audio/wav")}
    )
    assert resp.status_code == 201, resp.text
    scan_id = resp.json()["data"]["scan"]["id"]
    await scans_jobs_module.run_preprocessing_job(uuid.UUID(scan_id), db_session.bind)
    return scan_id


async def _start_processing(db_session: AsyncSession, scan_id: str):
    scan = await scans_repository.get_by_id(db_session, uuid.UUID(scan_id))
    scan = await inference_service.start_processing(db_session, scan)
    await db_session.commit()
    return scan


async def _register_and_activate_audio_cnn(db_session: AsyncSession, audio_cnn_checkpoint) -> None:
    await model_registry.register_model_version(
        db_session, architecture="AudioCNN", name="audio_cnn", version="v1", checkpoint_path=audio_cnn_checkpoint
    )
    await model_registry.switch_active_model(db_session, name="audio_cnn", version="v1")


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_audio_cnn_pipeline_reaches_completed_with_canonical_labels(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, audio_cnn_checkpoint
):
    await _register_verify_login(client, captured_emails, email="audiocnn@example.com")
    await _register_and_activate_audio_cnn(db_session, audio_cnn_checkpoint)

    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)
    scan = await _start_processing(db_session, scan_id)

    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)
    await db_session.refresh(scan)

    assert scan.status is ScanStatus.COMPLETED

    result = await inference_repository.get_result_by_scan_id(db_session, scan.id)
    assert result is not None
    # The whole point of convert_prediction(): AudioCNN's native
    # "Genuine"/"Deepfake" vocabulary must never reach persistence — only
    # VoiceGuard's canonical bonafide/spoof strings, satisfying the existing
    # ck_scan_results_label CHECK constraint unmodified.
    assert result.label in ("bonafide", "spoof")
    assert result.verdict in ("human", "ai_generated", "uncertain")
    assert 0.0 <= result.confidence <= 1.0
    assert result.feature_extractor_name == "logmel64db"

    model_version = await inference_repository.get_model_version_by_id(db_session, result.model_version_id)
    assert model_version.architecture == "AudioCNN"

    feature_vector = (
        await db_session.execute(select(FeatureVector).where(FeatureVector.scan_id == scan.id))
    ).scalar_one()
    assert feature_vector.extractor_name == "logmel64db"

    failures = (
        await db_session.execute(select(ProcessingFailure).where(ProcessingFailure.scan_id == scan.id))
    ).scalars().all()
    assert failures == []


async def test_audio_cnn_pipeline_explanation_is_gracefully_unavailable(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, audio_cnn_checkpoint
):
    """Phase 8: no rushed Grad-CAM port — the scan must still reach
    COMPLETED, with an explanation payload that clearly says explainability
    isn't available for this architecture, rather than failing or silently
    omitting the field."""
    await _register_verify_login(client, captured_emails, email="audiocnn-explain@example.com")
    await _register_and_activate_audio_cnn(db_session, audio_cnn_checkpoint)

    scan_id = await _upload_and_reach_ready_for_ai(client, db_session, tone=3100)
    scan = await _start_processing(db_session, scan_id)
    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)
    await db_session.refresh(scan)
    assert scan.status is ScanStatus.COMPLETED

    result = await inference_repository.get_result_by_scan_id(db_session, scan.id)
    assert result.explanation["salient_regions"] == []
    assert len(result.explanation["warnings"]) == 1
    assert "AudioCNN" in result.explanation["warnings"][0]

    metrics = (
        await db_session.execute(
            select(ProcessingMetric).where(
                ProcessingMetric.scan_id == scan.id, ProcessingMetric.stage == "generating_explanation"
            )
        )
    ).scalars().all()
    # The stage still ran and succeeded — "unavailable" is a successful
    # result, not a failure.
    assert len(metrics) == 1
    assert metrics[0].status == "succeeded"

    events = (
        await db_session.execute(select(ScanEvent).where(ScanEvent.scan_id == scan.id).order_by(ScanEvent.occurred_at))
    ).scalars().all()
    assert ("generating_explanation", "saving_results") in [(e.from_status, e.to_status) for e in events]


async def test_audio_cnn_result_response_reports_its_own_architecture(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, audio_cnn_checkpoint
):
    await _register_verify_login(client, captured_emails, email="audiocnn-service@example.com")
    await _register_and_activate_audio_cnn(db_session, audio_cnn_checkpoint)

    scan_id = await _upload_and_reach_ready_for_ai(client, db_session, tone=1800)
    scan = await _start_processing(db_session, scan_id)
    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)
    await db_session.refresh(scan)

    result, model_version = await inference_service.get_result(db_session, scan)
    assert result.scan_id == scan.id
    assert model_version.name == "audio_cnn"
    assert model_version.architecture == "AudioCNN"


# ── Coexistence: both architectures run correctly in the same process ──────


async def test_lcnn_and_audio_cnn_pipelines_coexist_without_cross_contamination(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, ai_checkpoint, audio_cnn_checkpoint
):
    """The strongest possible regression guard for "LCNN behavior is
    completely unchanged": run an LCNN scan to completion, switch the active
    model to AudioCNN, run a second scan to completion, and verify each
    scan's persisted result reflects the model that was actually active for
    *that* scan — not a stale cache, not the wrong adapter, not the wrong
    feature extractor."""
    await _register_verify_login(client, captured_emails, email="coexist@example.com")

    # LCNN is active by default once bootstrapped.
    await model_registry.get_active_model_version(db_session)

    lcnn_scan_id = await _upload_and_reach_ready_for_ai(client, db_session, tone=4200)
    lcnn_scan = await _start_processing(db_session, lcnn_scan_id)
    await jobs_module.run_ai_pipeline_job(lcnn_scan.id, db_session.bind)
    await db_session.refresh(lcnn_scan)
    assert lcnn_scan.status is ScanStatus.COMPLETED

    lcnn_result, lcnn_model_version = await inference_service.get_result(db_session, lcnn_scan)
    assert lcnn_model_version.architecture == "LCNN"
    assert lcnn_result.feature_extractor_name == "logmel"

    # Switch — a data operation, no code/deploy involved.
    await _register_and_activate_audio_cnn(db_session, audio_cnn_checkpoint)

    audio_scan_id = await _upload_and_reach_ready_for_ai(client, db_session, tone=900)
    audio_scan = await _start_processing(db_session, audio_scan_id)
    await jobs_module.run_ai_pipeline_job(audio_scan.id, db_session.bind)
    await db_session.refresh(audio_scan)
    assert audio_scan.status is ScanStatus.COMPLETED

    audio_result, audio_model_version = await inference_service.get_result(db_session, audio_scan)
    assert audio_model_version.architecture == "AudioCNN"
    assert audio_result.feature_extractor_name == "logmel64db"

    # The first scan's already-persisted result must be untouched by the
    # later switch.
    lcnn_result_again, lcnn_model_version_again = await inference_service.get_result(db_session, lcnn_scan)
    assert lcnn_result_again.id == lcnn_result.id
    assert lcnn_model_version_again.architecture == "LCNN"
