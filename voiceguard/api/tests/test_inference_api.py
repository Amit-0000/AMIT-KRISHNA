from __future__ import annotations

import io
import struct
import uuid
import wave
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.inference import jobs as jobs_module
from api.scans import jobs as scans_jobs_module
from api.scans import repository as scans_repository

pytestmark = pytest.mark.asyncio


def _wav_bytes(seconds: float = 1.0, rate: int = 16000, tone: int = 4000) -> bytes:
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


async def _upload_and_reach_ready_for_ai(client: AsyncClient, db_session: AsyncSession) -> str:
    resp = await client.post("/api/v1/scans", files={"file": ("clip.wav", _wav_bytes(), "audio/wav")})
    assert resp.status_code == 201, resp.text
    scan_id = resp.json()["data"]["scan"]["id"]
    await scans_jobs_module.run_preprocessing_job(uuid.UUID(scan_id), db_session.bind)
    return scan_id


async def _complete_scan(client: AsyncClient, db_session: AsyncSession) -> str:
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)
    resp = await client.post(f"/api/v1/scans/{scan_id}/process")
    assert resp.status_code == 202, resp.text
    scan = await scans_repository.get_by_id(db_session, uuid.UUID(scan_id))
    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)
    return scan_id


# ── POST /process ────────────────────────────────────────────────────────────


async def test_process_requires_authentication(client: AsyncClient):
    resp = await client.post(f"/api/v1/scans/{uuid.uuid4()}/process")
    assert resp.status_code == 401


async def test_process_returns_404_for_nonexistent_scan(client: AsyncClient, captured_emails):
    await _register_verify_login(client, captured_emails, email="a@example.com")
    resp = await client.post(f"/api/v1/scans/{uuid.uuid4()}/process")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SCAN_NOT_FOUND"


async def test_process_returns_404_for_another_users_scan(
    client: AsyncClient, captured_emails, db_session: AsyncSession
):
    await _register_verify_login(client, captured_emails, email="owner@example.com")
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)

    captured_emails.clear()
    await _register_verify_login(client, captured_emails, email="intruder@example.com")
    resp = await client.post(f"/api/v1/scans/{scan_id}/process")
    assert resp.status_code == 404


async def test_process_rejects_scan_not_ready_for_ai(client: AsyncClient, captured_emails, db_session: AsyncSession):
    """A scan that isn't READY_FOR_AI must be rejected before any model is
    touched. Uses a cancelled scan rather than a freshly-uploaded one to get
    a deterministic non-ready status: Slice 02's own preprocessing runs as a
    FastAPI BackgroundTask, which — per test_scans.py's own
    _run_preprocessing docstring — isn't guaranteed to still be QUEUED by
    the time this request fires, so asserting against that race would be
    flaky."""
    await _register_verify_login(client, captured_emails, email="b@example.com")
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)
    cancel_resp = await client.post(f"/api/v1/scans/{scan_id}/cancel")
    assert cancel_resp.status_code == 200

    process_resp = await client.post(f"/api/v1/scans/{scan_id}/process")
    assert process_resp.status_code == 422
    assert process_resp.json()["error"]["code"] == "SCAN_NOT_READY_FOR_PROCESSING"


async def test_process_accepted_transitions_scan_to_preparing_model(
    client: AsyncClient, captured_emails, db_session: AsyncSession, ai_checkpoint
):
    await _register_verify_login(client, captured_emails, email="c@example.com")
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)

    resp = await client.post(f"/api/v1/scans/{scan_id}/process")
    assert resp.status_code == 202
    body = resp.json()["data"]["scan"]
    assert body["scan_id"] == scan_id
    assert body["status"] == "preparing_model"


async def test_process_twice_rejects_the_second_call(
    client: AsyncClient, captured_emails, db_session: AsyncSession, ai_checkpoint
):
    await _register_verify_login(client, captured_emails, email="d@example.com")
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)

    first = await client.post(f"/api/v1/scans/{scan_id}/process")
    assert first.status_code == 202

    second = await client.post(f"/api/v1/scans/{scan_id}/process")
    assert second.status_code == 422
    assert second.json()["error"]["code"] == "SCAN_NOT_READY_FOR_PROCESSING"


# ── GET /result, /technical, /explanation ────────────────────────────────────


async def test_result_returns_404_before_processing_completes(
    client: AsyncClient, captured_emails, db_session: AsyncSession
):
    await _register_verify_login(client, captured_emails, email="e@example.com")
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)

    resp = await client.get(f"/api/v1/scans/{scan_id}/result")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESULT_NOT_FOUND"


async def test_result_available_after_completion(client: AsyncClient, captured_emails, db_session: AsyncSession, ai_checkpoint):
    await _register_verify_login(client, captured_emails, email="f@example.com")
    scan_id = await _complete_scan(client, db_session)

    resp = await client.get(f"/api/v1/scans/{scan_id}/result")
    assert resp.status_code == 200
    result = resp.json()["data"]["result"]
    assert result["scan_id"] == scan_id
    assert result["verdict"] in ("human", "ai_generated", "uncertain")
    assert "model_version" in result


async def test_result_not_visible_to_another_user(client: AsyncClient, captured_emails, db_session: AsyncSession, ai_checkpoint):
    await _register_verify_login(client, captured_emails, email="g@example.com")
    scan_id = await _complete_scan(client, db_session)

    captured_emails.clear()
    await _register_verify_login(client, captured_emails, email="intruder2@example.com")
    resp = await client.get(f"/api/v1/scans/{scan_id}/result")
    assert resp.status_code == 404


async def test_technical_includes_raw_scores_and_stage_timings(
    client: AsyncClient, captured_emails, db_session: AsyncSession, ai_checkpoint
):
    await _register_verify_login(client, captured_emails, email="h@example.com")
    scan_id = await _complete_scan(client, db_session)

    resp = await client.get(f"/api/v1/scans/{scan_id}/technical")
    assert resp.status_code == 200
    technical = resp.json()["data"]["technical"]
    assert 0.0 <= technical["raw_bonafide_score"] <= 1.0
    assert 0.0 <= technical["raw_spoof_score"] <= 1.0
    assert technical["model_name"] == "lcnn"
    assert len(technical["stage_timings"]) == 8  # one per AI_PIPELINE_STAGES entry


async def test_explanation_includes_notes_and_regions(
    client: AsyncClient, captured_emails, db_session: AsyncSession, ai_checkpoint
):
    await _register_verify_login(client, captured_emails, email="i@example.com")
    scan_id = await _complete_scan(client, db_session)

    resp = await client.get(f"/api/v1/scans/{scan_id}/explanation")
    assert resp.status_code == 200
    explanation = resp.json()["data"]["explanation"]
    assert len(explanation["notes"]) >= 1
    assert explanation["feature_extractor"] == "logmel:v1"


# ── GET /models, /models/current ─────────────────────────────────────────────


async def test_list_models_requires_authentication(client: AsyncClient):
    resp = await client.get("/api/v1/models")
    assert resp.status_code == 401


async def test_list_models_empty_without_a_checkpoint(client: AsyncClient, captured_emails):
    await _register_verify_login(client, captured_emails, email="j@example.com")
    resp = await client.get("/api/v1/models")
    assert resp.status_code == 200
    assert resp.json()["data"]["models"] == []


async def test_current_model_reports_unavailable_without_a_checkpoint(client: AsyncClient, captured_emails):
    await _register_verify_login(client, captured_emails, email="k@example.com")
    resp = await client.get("/api/v1/models/current")
    assert resp.status_code == 200
    assert resp.json()["data"]["model"]["available"] is False


async def test_current_model_reports_available_after_a_scan_is_processed(
    client: AsyncClient, captured_emails, db_session: AsyncSession, ai_checkpoint
):
    await _register_verify_login(client, captured_emails, email="l@example.com")
    await _complete_scan(client, db_session)

    resp = await client.get("/api/v1/models/current")
    assert resp.status_code == 200
    model = resp.json()["data"]["model"]
    assert model["available"] is True
    assert model["status"] == "active"

    list_resp = await client.get("/api/v1/models")
    models = list_resp.json()["data"]["models"]
    assert len(models) == 1
    assert models[0]["name"] == "lcnn"
    assert models[0]["status"] == "active"


# ── Multi-model: AudioCNN driving the exact same API surface ────────────────
# No new endpoints, no renamed endpoints — the same six routes covered above
# for LCNN, exercised again with a different active model to prove the API
# layer never needed to know which architecture produced the result.


async def _complete_scan_with_audio_cnn(client: AsyncClient, db_session: AsyncSession, audio_cnn_checkpoint) -> str:
    from api.inference import model_registry

    await model_registry.register_model_version(
        db_session, architecture="AudioCNN", name="audio_cnn", version="v1", checkpoint_path=audio_cnn_checkpoint
    )
    await model_registry.switch_active_model(db_session, name="audio_cnn", version="v1")
    return await _complete_scan(client, db_session)


async def test_result_available_after_completion_with_audio_cnn_active(
    client: AsyncClient, captured_emails, db_session: AsyncSession, audio_cnn_checkpoint
):
    await _register_verify_login(client, captured_emails, email="m@example.com")
    scan_id = await _complete_scan_with_audio_cnn(client, db_session, audio_cnn_checkpoint)

    resp = await client.get(f"/api/v1/scans/{scan_id}/result")
    assert resp.status_code == 200
    result = resp.json()["data"]["result"]
    assert result["scan_id"] == scan_id
    assert result["verdict"] in ("human", "ai_generated", "uncertain")
    assert result["model_version"] == "audio_cnn:v1"


async def test_technical_reports_audio_cnn_provenance(
    client: AsyncClient, captured_emails, db_session: AsyncSession, audio_cnn_checkpoint
):
    await _register_verify_login(client, captured_emails, email="n@example.com")
    scan_id = await _complete_scan_with_audio_cnn(client, db_session, audio_cnn_checkpoint)

    resp = await client.get(f"/api/v1/scans/{scan_id}/technical")
    assert resp.status_code == 200
    technical = resp.json()["data"]["technical"]
    assert technical["label"] in ("bonafide", "spoof")  # never "Genuine"/"Deepfake"
    assert technical["model_name"] == "audio_cnn"
    assert technical["model_architecture"] == "AudioCNN"
    assert technical["feature_extractor_name"] == "logmel64db"
    assert len(technical["stage_timings"]) == 8


async def test_explanation_reports_unavailable_for_audio_cnn(
    client: AsyncClient, captured_emails, db_session: AsyncSession, audio_cnn_checkpoint
):
    await _register_verify_login(client, captured_emails, email="o@example.com")
    scan_id = await _complete_scan_with_audio_cnn(client, db_session, audio_cnn_checkpoint)

    resp = await client.get(f"/api/v1/scans/{scan_id}/explanation")
    assert resp.status_code == 200
    explanation = resp.json()["data"]["explanation"]
    assert explanation["salient_regions"] == []
    assert len(explanation["warnings"]) == 1
    assert explanation["feature_extractor"] == "logmel64db:v1"


async def test_list_models_reports_both_architectures(
    client: AsyncClient, captured_emails, db_session: AsyncSession, ai_checkpoint, audio_cnn_checkpoint
):
    from api.inference import model_registry

    await _register_verify_login(client, captured_emails, email="p@example.com")
    await model_registry.get_active_model_version(db_session)  # bootstraps LCNN
    await model_registry.register_model_version(
        db_session, architecture="AudioCNN", name="audio_cnn", version="v1", checkpoint_path=audio_cnn_checkpoint
    )

    resp = await client.get("/api/v1/models")
    assert resp.status_code == 200
    models = {m["name"]: m for m in resp.json()["data"]["models"]}
    assert set(models.keys()) == {"lcnn", "audio_cnn"}
    assert models["lcnn"]["status"] == "active"
    assert models["audio_cnn"]["status"] == "inactive"
