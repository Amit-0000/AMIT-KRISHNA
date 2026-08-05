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
from api.scans import jobs as jobs_module
from api.scans.models import ProcessingJob, Scan, ScanEvent

pytestmark = pytest.mark.asyncio


async def _run_preprocessing(db_session: AsyncSession, scan_id: str) -> None:
    """FastAPI's BackgroundTasks aren't guaranteed to have completed by the
    time httpx's ASGI test transport returns a response (they run detached
    from the awaited call chain under this app's BaseHTTPMiddleware) — so
    tests that need to observe the *result* of preprocessing invoke the job
    directly instead of relying on incidental scheduling. run_preprocessing_job
    guards on scan.status == QUEUED, so this is safe even if the
    framework-scheduled copy also eventually runs."""
    await jobs_module.run_preprocessing_job(uuid.UUID(scan_id), db_session.bind)


def _wav_bytes(seconds: float = 0.5, rate: int = 16000, tone: int = 1000) -> bytes:
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
    from api.auth import service as auth_service

    captured: dict[str, str] = {}

    async def fake_verification_email(*, to: str, verification_url: str) -> None:
        captured["verification_url"] = verification_url

    monkeypatch.setattr(auth_service, "send_verification_email", fake_verification_email)
    return captured


async def _register_verify_login(
    client: AsyncClient, captured_emails: dict[str, str], *, email: str = "scanner@example.com"
) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Str0ng!Pass", "display_name": "Scanner"},
    )
    assert resp.status_code == 201, resp.text
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass"})
    assert login.status_code == 200, login.text


async def _upload(client: AsyncClient, *, filename="clip.wav", content=None, content_type="audio/wav"):
    if content is None:
        content = _wav_bytes()
    return await client.post("/api/v1/scans", files={"file": (filename, content, content_type)})


# ── Happy path / end-to-end ──────────────────────────────────────────────────


async def test_upload_reaches_ready_for_ai_with_extracted_metadata(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession
) -> None:
    await _register_verify_login(client, captured_emails)

    resp = await _upload(client, content=_wav_bytes(seconds=1.0, rate=16000))
    assert resp.status_code == 201, resp.text
    created = resp.json()["data"]["scan"]
    assert created["status"] == "queued"

    await _run_preprocessing(db_session, created["id"])

    scan = (await client.get(f"/api/v1/scans/{created['id']}")).json()["data"]["scan"]
    assert scan["status"] == "ready_for_ai"
    assert scan["duration_seconds"] == pytest.approx(1.0, abs=0.01)
    assert scan["scan_metadata"]["sample_rate"] == 16000
    assert scan["scan_metadata"]["channels"] == 1
    assert scan["file_size_bytes"] > 0
    assert len(scan["sha256_checksum"]) == 64
    assert scan["original_filename"] == "clip.wav"


async def test_get_scan_and_status_endpoint(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails)
    created = (await _upload(client)).json()["data"]["scan"]

    full = await client.get(f"/api/v1/scans/{created['id']}")
    assert full.status_code == 200
    assert full.json()["data"]["scan"]["id"] == created["id"]

    status_only = await client.get(f"/api/v1/scans/{created['id']}/status")
    assert status_only.status_code == 200
    body = status_only.json()["data"]["scan"]
    assert set(body.keys()) == {"id", "status", "error_code", "error_message", "updated_at"}


async def test_scan_events_record_full_transition_history(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession
) -> None:
    await _register_verify_login(client, captured_emails)
    scan_id = (await _upload(client)).json()["data"]["scan"]["id"]
    await _run_preprocessing(db_session, scan_id)

    result = await db_session.execute(
        select(ScanEvent).where(ScanEvent.scan_id == uuid.UUID(scan_id)).order_by(ScanEvent.occurred_at)
    )
    events = result.scalars().all()
    assert [(e.from_status, e.to_status) for e in events] == [
        ("created", "validating"),
        ("validating", "uploading"),
        ("uploading", "queued"),
        ("queued", "preprocessing"),
        ("preprocessing", "ready_for_ai"),
    ]


async def test_processing_job_row_recorded_as_succeeded(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession
) -> None:
    await _register_verify_login(client, captured_emails)
    scan_id = (await _upload(client)).json()["data"]["scan"]["id"]
    await _run_preprocessing(db_session, scan_id)

    result = await db_session.execute(select(ProcessingJob).where(ProcessingJob.scan_id == uuid.UUID(scan_id)))
    job = result.scalar_one()
    assert job.status == "succeeded"
    assert job.attempts == 1


async def test_scan_submitted_audit_log_written(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession
) -> None:
    await _register_verify_login(client, captured_emails)
    await _upload(client)

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.event_type == AuditEventType.SCAN_SUBMITTED.value)
    )
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].outcome == "success"


# ── Upload validation ─────────────────────────────────────────────────────────


async def test_unsupported_extension_rejected(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails)
    resp = await _upload(client, filename="malware.exe", content=b"not audio", content_type="application/octet-stream")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


async def test_empty_file_rejected(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails)
    resp = await _upload(client, content=b"")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "EMPTY_FILE"


async def test_too_small_file_rejected(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails)
    resp = await _upload(client, content=b"RIFF")  # well under MIN_UPLOAD_SIZE_BYTES, non-empty
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "FILE_TOO_SMALL"


async def test_too_large_file_rejected(
    client: AsyncClient, captured_emails: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_SIZE_BYTES", "100")
    get_settings.cache_clear()
    await _register_verify_login(client, captured_emails)
    resp = await _upload(client, content=_wav_bytes(seconds=1.0))  # >> 100 bytes
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "FILE_TOO_LARGE"


async def test_extension_mime_mismatch_rejected(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails)
    resp = await _upload(client, content=_wav_bytes(), content_type="text/html")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "EXTENSION_MIME_MISMATCH"


async def test_ambiguous_content_type_is_not_treated_as_mismatch(
    client: AsyncClient, captured_emails: dict[str, str]
) -> None:
    await _register_verify_login(client, captured_emails)
    resp = await _upload(client, content=_wav_bytes(), content_type="application/octet-stream")
    assert resp.status_code == 201


async def test_duplicate_upload_rejected_and_references_original(
    client: AsyncClient, captured_emails: dict[str, str]
) -> None:
    await _register_verify_login(client, captured_emails)
    content = _wav_bytes(seconds=1.0)
    first = await _upload(client, content=content)
    assert first.status_code == 201
    first_id = first.json()["data"]["scan"]["id"]

    second = await _upload(client, content=content)
    assert second.status_code == 409
    body = second.json()["error"]
    assert body["code"] == "DUPLICATE_UPLOAD"
    assert first_id in body["details"][0]["message"]


async def test_failed_upload_still_visible_in_history(
    client: AsyncClient, captured_emails: dict[str, str]
) -> None:
    """A rejected upload still leaves a terminal-state scan behind — the
    request errors out, but the attempt is visible in the user's history
    (this is exactly the pattern that write_audit_log's rollback-survival
    fix generalizes to: what happened must be persisted even when the
    request itself ultimately raises)."""
    await _register_verify_login(client, captured_emails)
    await _upload(client, content=b"")  # EMPTY_FILE, 400

    listing = await client.get("/api/v1/scans")
    scans = listing.json()["data"]["scans"]
    assert len(scans) == 1
    assert scans[0]["status"] == "validation_failed"
    assert scans[0]["error_code"] == "EMPTY_FILE"


async def test_malicious_filename_is_sanitized(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails)
    resp = await _upload(client, filename="../../../etc/passwd.wav")
    assert resp.status_code == 201
    stored_name = resp.json()["data"]["scan"]["original_filename"]
    assert "/" not in stored_name
    assert ".." not in stored_name


# ── Authorization / ownership ─────────────────────────────────────────────────


async def test_create_scan_requires_authentication(client: AsyncClient) -> None:
    resp = await _upload(client)
    assert resp.status_code == 401


async def test_list_scans_requires_authentication(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/scans")
    assert resp.status_code == 401


async def test_cannot_access_another_users_scan(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails, email="owner@example.com")
    owned_id = (await _upload(client)).json()["data"]["scan"]["id"]

    captured_emails.clear()
    await _register_verify_login(client, captured_emails, email="intruder@example.com")

    resp = await client.get(f"/api/v1/scans/{owned_id}")
    assert resp.status_code == 404  # not 403 — existence is not confirmed to a non-owner

    listing = await client.get("/api/v1/scans")
    assert listing.json()["data"]["scans"] == []


async def test_cannot_cancel_another_users_scan(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails, email="owner2@example.com")
    owned_id = (await _upload(client)).json()["data"]["scan"]["id"]

    captured_emails.clear()
    await _register_verify_login(client, captured_emails, email="intruder2@example.com")

    resp = await client.post(f"/api/v1/scans/{owned_id}/cancel")
    assert resp.status_code == 404


async def test_get_nonexistent_scan_returns_404(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails)
    resp = await client.get("/api/v1/scans/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SCAN_NOT_FOUND"


# ── Cancel / delete / state transitions ──────────────────────────────────────


async def test_cancel_scan_succeeds_then_rejects_second_cancel(
    client: AsyncClient, captured_emails: dict[str, str]
) -> None:
    await _register_verify_login(client, captured_emails)
    scan_id = (await _upload(client)).json()["data"]["scan"]["id"]

    first = await client.post(f"/api/v1/scans/{scan_id}/cancel")
    assert first.status_code == 200
    assert first.json()["data"]["scan"]["status"] == "cancelled"

    second = await client.post(f"/api/v1/scans/{scan_id}/cancel")
    assert second.status_code == 422
    assert second.json()["error"]["code"] == "INVALID_SCAN_STATE"


async def test_delete_scan_soft_deletes_and_404s_afterward(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession
) -> None:
    await _register_verify_login(client, captured_emails)
    scan_id = (await _upload(client)).json()["data"]["scan"]["id"]

    resp = await client.delete(f"/api/v1/scans/{scan_id}")
    assert resp.status_code == 200

    assert (await client.get(f"/api/v1/scans/{scan_id}")).status_code == 404

    # Soft delete, not a hard delete — the row (and its history) still exists.
    row = await db_session.get(Scan, uuid.UUID(scan_id))
    assert row is not None
    assert row.deleted_at is not None


async def test_delete_nonterminal_scan_cancels_it_first(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession
) -> None:
    await _register_verify_login(client, captured_emails)
    scan_id = (await _upload(client)).json()["data"]["scan"]["id"]

    # The framework-scheduled background task may or may not have completed
    # by now (see _run_preprocessing's docstring — its timing isn't
    # deterministic from the test's perspective), so this could legitimately
    # be QUEUED or already READY_FOR_AI. Either way it must be non-terminal,
    # which is the precondition this test actually cares about.
    pre_delete = await db_session.get(Scan, uuid.UUID(scan_id))
    assert pre_delete.status.value in {"queued", "ready_for_ai"}

    resp = await client.delete(f"/api/v1/scans/{scan_id}")
    assert resp.status_code == 200

    await db_session.refresh(pre_delete)
    assert pre_delete.status.value == "cancelled"
    assert pre_delete.deleted_at is not None


# ── Pagination / filtering / sorting ──────────────────────────────────────────


async def test_list_pagination_filtering_and_sorting(
    client: AsyncClient, captured_emails: dict[str, str]
) -> None:
    await _register_verify_login(client, captured_emails)
    for i in range(3):
        resp = await _upload(client, content=_wav_bytes(seconds=0.2 + i * 0.1, tone=1000 + i))
        assert resp.status_code == 201

    first_page = await client.get("/api/v1/scans", params={"page": 1, "page_size": 2})
    assert first_page.status_code == 200
    meta = first_page.json()["meta"]
    assert meta == {"page": 1, "page_size": 2, "total": 3, "total_pages": 2}
    assert len(first_page.json()["data"]["scans"]) == 2

    second_page = await client.get("/api/v1/scans", params={"page": 2, "page_size": 2})
    assert len(second_page.json()["data"]["scans"]) == 1

    newest_first = await client.get("/api/v1/scans", params={"sort": "-created_at"})
    oldest_first = await client.get("/api/v1/scans", params={"sort": "created_at"})
    newest_ids = [s["id"] for s in newest_first.json()["data"]["scans"]]
    oldest_ids = [s["id"] for s in oldest_first.json()["data"]["scans"]]
    assert newest_ids == list(reversed(oldest_ids))

    any_scan_id = newest_ids[0]
    await client.post(f"/api/v1/scans/{any_scan_id}/cancel")
    cancelled_only = await client.get("/api/v1/scans", params={"status": "cancelled"})
    assert len(cancelled_only.json()["data"]["scans"]) == 1
    assert cancelled_only.json()["data"]["scans"][0]["status"] == "cancelled"


# ── Rate limiting ─────────────────────────────────────────────────────────────


async def test_scan_create_rate_limit_enforced(
    client: AsyncClient, captured_emails: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RATE_LIMIT_SCAN_CREATE_PER_HOUR_PER_USER", "2")
    get_settings.cache_clear()
    await _register_verify_login(client, captured_emails)

    for i in range(2):
        resp = await _upload(client, content=_wav_bytes(seconds=0.3 + i * 0.1, tone=2000 + i))
        assert resp.status_code == 201, resp.text

    over_limit = await _upload(client, content=_wav_bytes(seconds=0.9, tone=3000))
    assert over_limit.status_code == 429
    assert over_limit.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Retry-After" in over_limit.headers


# ── Preprocessing failure / retry ─────────────────────────────────────────────


async def test_preprocessing_failure_exhausts_retries_and_marks_scan_failed(
    client: AsyncClient, captured_emails: dict[str, str], monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
) -> None:
    call_count = 0

    async def _always_fails(scan) -> None:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("simulated preprocessing outage")

    monkeypatch.setattr(jobs_module, "_run_preprocessing_once", _always_fails)
    monkeypatch.setenv("PREPROCESSING_MAX_ATTEMPTS", "2")
    get_settings.cache_clear()

    await _register_verify_login(client, captured_emails)
    resp = await _upload(client)
    assert resp.status_code == 201
    scan_id = resp.json()["data"]["scan"]["id"]

    await _run_preprocessing(db_session, scan_id)

    scan = (await client.get(f"/api/v1/scans/{scan_id}")).json()["data"]["scan"]
    assert scan["status"] == "failed"
    assert scan["error_code"] == "PREPROCESSING_FAILED"
    assert call_count == 2

    job_row = (
        await db_session.execute(select(ProcessingJob).where(ProcessingJob.scan_id == uuid.UUID(scan_id)))
    ).scalar_one()
    assert job_row.status == "failed"
    assert job_row.attempts == 2

    events = (
        await db_session.execute(
            select(ScanEvent).where(ScanEvent.scan_id == uuid.UUID(scan_id)).order_by(ScanEvent.occurred_at)
        )
    ).scalars().all()
    assert [(e.from_status, e.to_status) for e in events][-2:] == [
        ("queued", "preprocessing"),
        ("preprocessing", "failed"),
    ]


async def test_preprocessing_succeeds_on_second_attempt(
    client: AsyncClient, captured_emails: dict[str, str], monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
) -> None:
    attempts = {"count": 0}
    real_run = jobs_module._run_preprocessing_once

    async def _fails_once_then_succeeds(scan) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient failure")
        await real_run(scan)

    monkeypatch.setattr(jobs_module, "_run_preprocessing_once", _fails_once_then_succeeds)
    monkeypatch.setenv("PREPROCESSING_MAX_ATTEMPTS", "3")
    get_settings.cache_clear()

    await _register_verify_login(client, captured_emails)
    resp = await _upload(client)
    assert resp.status_code == 201
    scan_id = resp.json()["data"]["scan"]["id"]

    await _run_preprocessing(db_session, scan_id)

    scan = (await client.get(f"/api/v1/scans/{scan_id}")).json()["data"]["scan"]
    assert scan["status"] == "ready_for_ai"
    assert attempts["count"] == 2
