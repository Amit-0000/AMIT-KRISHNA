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

from api.core.audit import AuditEventType, AuditLog
from api.core.config import get_settings
from api.inference import jobs as jobs_module
from api.inference import repository as inference_repository
from api.inference import service as inference_service
from api.inference.models import FeatureVector, ProcessingFailure, ProcessingMetric
from api.scans import repository as scans_repository
from api.scans.models import Scan, ScanEvent
from api.scans.state_machine import AI_PIPELINE_STAGES, ScanStatus

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


async def _register_verify_login(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "ai-pipeline@example.com", "password": "Str0ng!Pass", "display_name": "AI Tester"},
    )
    assert resp.status_code == 201, resp.text
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    login = await client.post("/api/v1/auth/login", json={"email": "ai-pipeline@example.com", "password": "Str0ng!Pass"})
    assert login.status_code == 200, login.text


async def _upload_and_reach_ready_for_ai(client: AsyncClient, db_session: AsyncSession) -> str:
    """Drives a scan through Slice 02's upload pipeline (real HTTP calls,
    real preprocessing job) up to READY_FOR_AI — the exact handoff point
    this slice's pipeline picks up from."""
    from api.scans import jobs as scans_jobs_module

    resp = await client.post(
        "/api/v1/scans", files={"file": ("clip.wav", _wav_bytes(seconds=1.0), "audio/wav")}
    )
    assert resp.status_code == 201, resp.text
    scan_id = resp.json()["data"]["scan"]["id"]

    await scans_jobs_module.run_preprocessing_job(uuid.UUID(scan_id), db_session.bind)

    scan = await scans_repository.get_by_id(db_session, uuid.UUID(scan_id))
    assert scan.status is ScanStatus.READY_FOR_AI, f"expected ready_for_ai, got {scan.status.value}"
    return scan_id


async def _start_processing(db_session: AsyncSession, scan_id: str) -> Scan:
    scan = await scans_repository.get_by_id(db_session, uuid.UUID(scan_id))
    scan = await inference_service.start_processing(db_session, scan)
    await db_session.commit()
    return scan


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_full_pipeline_reaches_completed_and_persists_result(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, ai_checkpoint
):
    await _register_verify_login(client, captured_emails)
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)
    scan = await _start_processing(db_session, scan_id)

    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)
    await db_session.refresh(scan)

    assert scan.status is ScanStatus.COMPLETED

    result = await inference_repository.get_result_by_scan_id(db_session, scan.id)
    assert result is not None
    assert result.verdict in ("human", "ai_generated", "uncertain")
    assert result.label in ("bonafide", "spoof")
    assert 0.0 <= result.confidence <= 1.0
    assert result.processing_time_ms >= 0
    assert result.inference_time_ms >= 0

    feature_vector = (
        await db_session.execute(select(FeatureVector).where(FeatureVector.scan_id == scan.id))
    ).scalar_one()
    assert feature_vector.extractor_name == "logmel"
    assert feature_vector.storage_key is not None  # FEATURE_VECTOR_STORAGE_ENABLED defaults to True

    metrics = (
        await db_session.execute(select(ProcessingMetric).where(ProcessingMetric.scan_id == scan.id))
    ).scalars().all()
    stages_recorded = {m.stage for m in metrics}
    assert stages_recorded == {s.value for s in AI_PIPELINE_STAGES}
    assert all(m.status == "succeeded" for m in metrics)

    failures = (
        await db_session.execute(select(ProcessingFailure).where(ProcessingFailure.scan_id == scan.id))
    ).scalars().all()
    assert failures == []

    events = (
        await db_session.execute(select(ScanEvent).where(ScanEvent.scan_id == scan.id).order_by(ScanEvent.occurred_at))
    ).scalars().all()
    transition_pairs = [(e.from_status, e.to_status) for e in events]
    assert transition_pairs[-1] == ("saving_results", "completed")
    assert ("ready_for_ai", "preparing_model") in transition_pairs

    audit_logs = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.event_type == AuditEventType.SCAN_PROCESSING_COMPLETED.value)
        )
    ).scalars().all()
    assert len(audit_logs) == 1


async def test_result_response_matches_persisted_result(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, ai_checkpoint
):
    await _register_verify_login(client, captured_emails)
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)
    scan = await _start_processing(db_session, scan_id)
    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)
    await db_session.refresh(scan)

    result, model_version = await inference_service.get_result(db_session, scan)
    assert result.scan_id == scan.id
    assert model_version.name == get_settings().MODEL_NAME


# ── MALWARE_SCAN_REQUIRED=false: unscanned files still reach a real result ──


async def test_scan_unavailable_and_optional_still_reaches_completed_with_result(
    client: AsyncClient,
    captured_emails: dict[str, str],
    db_session: AsyncSession,
    ai_checkpoint,
    monkeypatch: pytest.MonkeyPatch,
):
    """Case D end-to-end: ClamAV unavailable + MALWARE_SCAN_REQUIRED=false
    must let the upload flow all the way to a real AI result (not just past
    the upload endpoint, per test_scans.py's
    test_scanner_unavailable_and_not_required_continues_unscanned), while the
    scan and its result both keep reporting NOT_SCANNED — never CLEAN — so
    nothing downstream can misread this as a verified-safe file."""
    from api.scans import malware_scan as malware_scan_module
    from api.scans.malware_scan import MalwareScanResult, MalwareScanStatus

    async def _fake_unavailable(storage, storage_key):
        return MalwareScanResult(status=MalwareScanStatus.UNAVAILABLE, engine="fake-clamav", detail="connection refused")

    monkeypatch.setattr(malware_scan_module, "scan_file", _fake_unavailable)
    monkeypatch.setenv("MALWARE_SCAN_REQUIRED", "false")
    get_settings.cache_clear()

    await _register_verify_login(client, captured_emails)
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)

    scan = await scans_repository.get_by_id(db_session, uuid.UUID(scan_id))
    assert scan.malware_scan_status == "not_scanned"

    scan = await _start_processing(db_session, scan_id)
    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)
    await db_session.refresh(scan)

    assert scan.status is ScanStatus.COMPLETED
    assert scan.malware_scan_status == "not_scanned"

    result = await inference_repository.get_result_by_scan_id(db_session, scan.id)
    assert result is not None
    assert result.verdict in ("human", "ai_generated", "uncertain")

    response = await client.get(f"/api/v1/scans/{scan.id}/result")
    assert response.status_code == 200, response.text
    body = response.json()["data"]["result"]
    assert body["malware_scan_status"] == "not_scanned"
    assert body["verdict"] in ("human", "ai_generated", "uncertain")


# ── No model available ───────────────────────────────────────────────────────


async def test_pipeline_fails_with_model_load_failed_when_no_checkpoint(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession
):
    """No ai_checkpoint fixture here — MODEL_CHECKPOINT_PATH points nowhere
    (see conftest._isolated_settings), mirroring a real deployment with no
    trained checkpoint yet."""
    await _register_verify_login(client, captured_emails)
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)
    scan = await _start_processing(db_session, scan_id)

    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)
    await db_session.refresh(scan)

    assert scan.status is ScanStatus.MODEL_LOAD_FAILED
    assert scan.error_code == "MODEL_NOT_AVAILABLE"

    failures = (
        await db_session.execute(select(ProcessingFailure).where(ProcessingFailure.scan_id == scan.id))
    ).scalars().all()
    # ModelNotAvailableError.retryable = False — must fail on the first
    # attempt rather than burning AI_STAGE_MAX_ATTEMPTS on a guaranteed
    # repeat failure.
    assert len(failures) == 1
    assert failures[0].retryable is False

    audit_logs = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.event_type == AuditEventType.SCAN_PROCESSING_FAILED.value)
        )
    ).scalars().all()
    assert len(audit_logs) == 1


# ── Retry then succeed ───────────────────────────────────────────────────────


async def test_pipeline_retries_a_transient_failure_then_succeeds(
    client: AsyncClient,
    captured_emails: dict[str, str],
    db_session: AsyncSession,
    ai_checkpoint,
    monkeypatch: pytest.MonkeyPatch,
):
    await _register_verify_login(client, captured_emails)
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)
    scan = await _start_processing(db_session, scan_id)

    real_extract = jobs_module.feature_extraction.extract_features
    calls = {"count": 0}

    def _fails_once_then_succeeds(waveform, *, extractor_name, extractor_version):
        calls["count"] += 1
        if calls["count"] == 1:
            from api.inference.exceptions import FeatureExtractionError

            raise FeatureExtractionError("simulated transient extraction failure")
        return real_extract(waveform, extractor_name=extractor_name, extractor_version=extractor_version)

    monkeypatch.setattr(jobs_module.feature_extraction, "extract_features", _fails_once_then_succeeds)

    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)
    await db_session.refresh(scan)

    assert scan.status is ScanStatus.COMPLETED
    assert calls["count"] == 2

    metrics = (
        await db_session.execute(
            select(ProcessingMetric)
            .where(ProcessingMetric.scan_id == scan.id, ProcessingMetric.stage == "feature_extraction")
            .order_by(ProcessingMetric.attempt)
        )
    ).scalars().all()
    assert [m.status for m in metrics] == ["failed", "succeeded"]
    assert [m.attempt for m in metrics] == [1, 2]


# ── Retry exhaustion ─────────────────────────────────────────────────────────


async def test_pipeline_exhausts_retries_and_lands_in_correct_failed_state(
    client: AsyncClient,
    captured_emails: dict[str, str],
    db_session: AsyncSession,
    ai_checkpoint,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AI_STAGE_MAX_ATTEMPTS", "2")
    get_settings.cache_clear()

    await _register_verify_login(client, captured_emails)
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)
    scan = await _start_processing(db_session, scan_id)

    def _always_fails(loaded_model, feature):
        from api.inference.exceptions import InferenceError

        raise InferenceError("simulated persistent inference outage")

    monkeypatch.setattr(jobs_module.inference, "run_inference", _always_fails)

    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)
    await db_session.refresh(scan)

    assert scan.status is ScanStatus.INFERENCE_FAILED
    assert scan.error_code == "INFERENCE_FAILED"
    assert scan.retry_count == 2

    failures = (
        await db_session.execute(
            select(ProcessingFailure).where(
                ProcessingFailure.scan_id == scan.id, ProcessingFailure.stage == "running_inference"
            )
        )
    ).scalars().all()
    assert len(failures) == 2
    assert [f.attempt for f in failures] == [1, 2]

    events = (
        await db_session.execute(select(ScanEvent).where(ScanEvent.scan_id == scan.id).order_by(ScanEvent.occurred_at))
    ).scalars().all()
    assert (events[-1].from_status, events[-1].to_status) == ("running_inference", "inference_failed")

    # Regression coverage for the same "notifications are permanently empty"
    # bug fixed for scan_complete (see test_notifications.py's
    # test_scan_completion_creates_a_notification) -- a scan that exhausts
    # retries and lands in a terminal *_FAILED state must also produce a
    # real, visible notification (api/inference/jobs.py's _run_stage
    # failure branch).
    list_resp = await client.get("/api/v1/notifications")
    assert list_resp.status_code == 200
    notifications = list_resp.json()["data"]
    assert len(notifications) == 1
    assert notifications[0]["type"] == "scan_failed"
    assert notifications[0]["read"] is False
    assert str(scan.id) in notifications[0]["action_url"]


# ── Timeout ───────────────────────────────────────────────────────────────────


async def test_pipeline_stage_timeout_is_recorded_and_retried(
    client: AsyncClient,
    captured_emails: dict[str, str],
    db_session: AsyncSession,
    ai_checkpoint,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AI_STAGE_TIMEOUT_S", "0.05")
    monkeypatch.setenv("AI_STAGE_MAX_ATTEMPTS", "2")
    get_settings.cache_clear()

    await _register_verify_login(client, captured_emails)
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)
    scan = await _start_processing(db_session, scan_id)

    async def _hangs(*args, **kwargs):
        import asyncio

        await asyncio.sleep(1.0)

    monkeypatch.setattr(jobs_module, "_stage_load_model", _hangs)

    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)
    await db_session.refresh(scan)

    assert scan.status is ScanStatus.MODEL_LOAD_FAILED
    assert scan.error_code == "AI_STAGE_TIMEOUT"

    failures = (
        await db_session.execute(
            select(ProcessingFailure).where(
                ProcessingFailure.scan_id == scan.id, ProcessingFailure.stage == "loading_model"
            )
        )
    ).scalars().all()
    assert len(failures) == 2
    assert all(f.error_code == "AI_STAGE_TIMEOUT" for f in failures)


# ── Unhandled exception safety net ──────────────────────────────────────────
# Regression coverage for the "Computing confidence ~48% forever" bug: a scan
# stuck in LOADING_MODEL indefinitely because api.inference.model_loader.
# load_model() let a raw ModuleNotFoundError (missing torch) escape past
# _run_stage's except AIPipelineError/asyncio.TimeoutError clauses and out of
# run_ai_pipeline_job entirely, as an unhandled exception inside a FastAPI
# BackgroundTask — which Starlette never logs or retries. See
# test_ai_model_loader.test_load_model_raises_model_not_available_when_ml_runtime_missing
# for the fix at its source (model_loader now converts that into a proper
# ModelNotAvailableError). This test instead covers the class of bug, not
# just this one instance: whatever *unexpected* exception type a stage body
# raises, run_ai_pipeline_job's own except Exception safety net must still
# land the scan in a terminal *_FAILED state and must never itself raise —
# so a future bug of the same shape, anywhere in the pipeline, fails loudly
# and visibly instead of hanging a scan forever again.


async def test_unexpected_exception_in_a_stage_still_reaches_a_terminal_state(
    client: AsyncClient,
    captured_emails: dict[str, str],
    db_session: AsyncSession,
    ai_checkpoint,
    monkeypatch: pytest.MonkeyPatch,
    caplog,
):
    await _register_verify_login(client, captured_emails)
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)
    scan = await _start_processing(db_session, scan_id)

    def _raises_something_run_once_never_catches(model_version):
        # Not an AIPipelineError, not asyncio.TimeoutError — exactly the
        # shape of bug _run_stage's except clauses can't see coming.
        raise RuntimeError("simulated unforeseen bug, not an AIPipelineError")

    monkeypatch.setattr(jobs_module, "_stage_load_model", _raises_something_run_once_never_catches)

    import logging

    with caplog.at_level(logging.ERROR, logger="voiceguard.inference"):
        # Must not raise — this is exactly what a FastAPI BackgroundTask
        # calls, uncaught, with no framework-level retry or error handling.
        await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)

    await db_session.refresh(scan)

    assert scan.status is ScanStatus.MODEL_LOAD_FAILED
    assert scan.status not in (ScanStatus.PREPARING_MODEL, ScanStatus.LOADING_MODEL)  # not stuck mid-pipeline
    assert scan.error_code == "AI_PROCESSING_ERROR"

    assert any(r.message == "ai_pipeline_unhandled_exception" for r in caplog.records)

    job = await scans_repository.get_latest_job(db_session, scan.id, job_type=inference_service.AI_JOB_TYPE)
    assert job.status == "failed"
    assert job.finished_at is not None

    events = (
        await db_session.execute(select(ScanEvent).where(ScanEvent.scan_id == scan.id).order_by(ScanEvent.occurred_at))
    ).scalars().all()
    assert (events[-1].from_status, events[-1].to_status) == ("loading_model", "model_load_failed")

    audit_logs = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.event_type == AuditEventType.SCAN_PROCESSING_FAILED.value)
        )
    ).scalars().all()
    assert len(audit_logs) == 1


# ── Unhandled exception with an already-broken DB transaction ──────────────
# Regression coverage for a defect found by actually running this suite (not
# by inspection): test_pipeline_stage_timeout_is_recorded_and_retried above
# occasionally (a genuinely timing-sensitive, non-deterministic interaction —
# not reliably reproducible via a plain rerun) hit a live
# sqlalchemy.exc.PendingRollbackError raised from *inside*
# run_ai_pipeline_job's own last-resort `except Exception` handler: that
# handler used to log `scan.id` (an ORM attribute read) before calling
# `db.rollback()`, and if `db`'s transaction was already DEACTIVE — which
# happens whenever a DBAPI-level error occurs mid-flush anywhere earlier in
# the same stage, not only under a timeout race — that attribute access
# itself raised a second exception from inside the code whose entire job is
# to guarantee a terminal state no matter what went wrong. This test forces
# that "failed session" condition directly (a CHECK-constraint violation on
# a flush, exactly the shape of error a real DBAPI failure mid-stage would
# leave behind) instead of relying on a razor-thin asyncio timeout, so the
# invariant is verified deterministically rather than only occasionally
# under load.


async def test_unhandled_exception_with_a_broken_transaction_does_not_raise_pendingrollbackerror(
    client: AsyncClient,
    captured_emails: dict[str, str],
    db_session: AsyncSession,
    ai_checkpoint,
    monkeypatch: pytest.MonkeyPatch,
    caplog,
):
    from sqlalchemy.exc import PendingRollbackError

    from api.scans.models import ScanEvent

    await _register_verify_login(client, captured_emails)
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)
    scan = await _start_processing(db_session, scan_id)

    async def _break_transaction_then_raise(db: AsyncSession):
        # Violates ck_scan_events_actor (actor IN ('user', 'system')) —
        # SQLite enforces CHECK constraints by default, so this flush fails
        # with a real IntegrityError, leaving `db`'s transaction DEACTIVE
        # ("...rolled back due to a previous exception during flush") until
        # something calls rollback() — exactly the state run_ai_pipeline_job's
        # last-resort handler must be able to recover from.
        db.add(ScanEvent(scan_id=scan.id, to_status="queued", actor="not-a-valid-actor"))
        try:
            await db.flush()
        except Exception:
            pass
        raise RuntimeError("simulated bug hitting an already-broken transaction")

    monkeypatch.setattr(jobs_module, "_stage_prepare_model", _break_transaction_then_raise)

    import logging

    with caplog.at_level(logging.ERROR, logger="voiceguard.inference"):
        # Must not raise -- and specifically must not raise
        # PendingRollbackError out of the handler meant to recover from it.
        await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)

    await db_session.refresh(scan)

    # Terminal state reached -- not stuck in a processing status.
    assert scan.status is ScanStatus.MODEL_LOAD_FAILED
    assert scan.error_code == "AI_PROCESSING_ERROR"

    # The original failure is still visible in the logs, not masked by a
    # secondary PendingRollbackError.
    unhandled_records = [r for r in caplog.records if r.message == "ai_pipeline_unhandled_exception"]
    assert len(unhandled_records) == 1
    assert not any(
        r.exc_info and isinstance(r.exc_info[1], PendingRollbackError) for r in caplog.records
    )

    job = await scans_repository.get_latest_job(db_session, scan.id, job_type=inference_service.AI_JOB_TYPE)
    assert job.status == "failed"
    assert job.finished_at is not None

    events = (
        await db_session.execute(select(ScanEvent).where(ScanEvent.scan_id == scan.id).order_by(ScanEvent.occurred_at))
    ).scalars().all()
    assert (events[-1].from_status, events[-1].to_status) == ("preparing_model", "model_load_failed")


# ── Cancellation mid-pipeline ────────────────────────────────────────────────


async def test_run_stage_aborts_when_scan_is_cancelled_concurrently(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, ai_checkpoint
):
    """White-box test of the per-attempt cancellation check inside
    api.inference.jobs._run_stage: a concurrent POST /scans/{id}/cancel (a
    separate session, exactly as it would be in a real request) commits
    CANCELLED while the job's own session still thinks it's mid-pipeline;
    the next stage attempt must notice on its db.refresh(scan) and abort
    rather than continuing to process (or worse, transitioning back out of
    CANCELLED)."""
    await _register_verify_login(client, captured_emails)
    scan_id = await _upload_and_reach_ready_for_ai(client, db_session)
    scan = await _start_processing(db_session, scan_id)

    # Simulate a concurrent cancel via a second, independent session bound
    # to the same engine — exactly how a real second HTTP request would
    # reach the same row.
    from api.scans.service import cancel_scan as scans_cancel_scan
    from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession

    async with _AsyncSession(bind=db_session.bind, expire_on_commit=False) as other_session:
        other_scan = await scans_repository.get_by_id(other_session, scan.id)
        await scans_cancel_scan(other_session, other_scan)
        await other_session.commit()

    job = await scans_repository.get_latest_job(db_session, scan.id, job_type=inference_service.AI_JOB_TYPE)

    with pytest.raises(jobs_module._PipelineAborted):
        await jobs_module._run_stage(
            db_session,
            scan,
            job,
            stage=ScanStatus.PREPARING_MODEL,
            run_once=lambda: jobs_module._stage_prepare_model(db_session),
            max_attempts=3,
            timeout_s=5.0,
            correlation_id="test-correlation-id",
        )

    # The CANCELLED status set by the concurrent request must survive —
    # _run_stage must not have overwritten it with anything.
    current = await scans_repository.get_by_id(db_session, scan.id)
    assert current.status is ScanStatus.CANCELLED
