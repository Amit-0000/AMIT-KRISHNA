from __future__ import annotations

import io
import struct
import uuid
import wave
from pathlib import Path
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
    from api.auth import service as auth_service

    captured: dict[str, str] = {}

    async def fake_verification_email(*, to: str, verification_url: str) -> None:
        captured["verification_url"] = verification_url

    monkeypatch.setattr(auth_service, "send_verification_email", fake_verification_email)
    return captured


async def _register_verify_login(client: AsyncClient, captured_emails: dict[str, str], *, email: str) -> None:
    await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "Str0ng!Pass", "display_name": "Tester"}
    )
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass"})


async def _complete_scan(client: AsyncClient, db_session: AsyncSession, *, seconds: float = 1.0) -> str:
    resp = await client.post("/api/v1/scans", files={"file": ("clip.wav", _wav_bytes(seconds), "audio/wav")})
    assert resp.status_code == 201, resp.text
    scan_id = resp.json()["data"]["scan"]["id"]
    await scans_jobs_module.run_preprocessing_job(uuid.UUID(scan_id), db_session.bind)

    process_resp = await client.post(f"/api/v1/scans/{scan_id}/process")
    assert process_resp.status_code == 202, process_resp.text
    scan = await scans_repository.get_by_id(db_session, uuid.UUID(scan_id))
    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)
    return scan_id


async def test_dashboard_requires_authentication(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/dashboard")
    assert resp.status_code == 401


async def test_dashboard_empty_state(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails, email="empty@example.com")
    resp = await client.get("/api/v1/dashboard")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["stats"]["total_scans"] == 0
    assert data["stats"]["ai_detected"] == 0
    assert len(data["trend"]) == 30
    assert len(data["confidence_distribution"]) == 10
    assert data["recent_activity"] == []
    assert data["model_status"]["health"] == "down"


async def test_dashboard_reflects_completed_scan(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, ai_checkpoint: Path
) -> None:
    await _register_verify_login(client, captured_emails, email="dash@example.com")
    scan_id = await _complete_scan(client, db_session)

    resp = await client.get("/api/v1/dashboard")
    data = resp.json()["data"]
    assert data["stats"]["total_scans"] == 1
    assert data["stats"]["ai_detected"] + data["stats"]["human_verified"] + data["stats"]["uncertain"] == 1
    assert len(data["recent_activity"]) == 1
    assert data["recent_activity"][0]["scan_id"] == scan_id
    assert data["model_status"]["health"] in ("healthy", "degraded")


async def test_recent_scans_endpoint(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, ai_checkpoint: Path
) -> None:
    await _register_verify_login(client, captured_emails, email="recent@example.com")
    scan_id = await _complete_scan(client, db_session)

    resp = await client.get("/api/v1/dashboard/recent-scans")
    assert resp.status_code == 200
    scans = resp.json()["data"]
    assert len(scans) == 1
    assert scans[0]["scan_id"] == scan_id
    assert scans[0]["status"] == "completed"
    assert scans[0]["file_name"] == "clip.wav"
    assert scans[0]["share_token"] is None


async def test_dashboard_stats_exclude_deleted_scans(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, ai_checkpoint: Path
) -> None:
    """Regression test for the "AI Detected: 133% of total" bug: deleting a
    completed scan must remove it from every dashboard stat consistently
    (total_scans, verdict counts, avg_processing_ms, trend, confidence
    distribution) — not just from total_scans while its ScanResult keeps
    counting toward the others forever."""
    await _register_verify_login(client, captured_emails, email="deleted-scan@example.com")
    kept_scan_id = await _complete_scan(client, db_session)
    # Different duration so this isn't byte-identical to the first upload
    # (identical uploads are rejected as duplicates — not what's under test).
    deleted_scan_id = await _complete_scan(client, db_session, seconds=1.5)

    before = (await client.get("/api/v1/dashboard")).json()["data"]
    assert before["stats"]["total_scans"] == 2
    verdict_total_before = (
        before["stats"]["ai_detected"] + before["stats"]["human_verified"] + before["stats"]["uncertain"]
    )
    assert verdict_total_before == 2

    del_resp = await client.delete(f"/api/v1/scans/{deleted_scan_id}")
    assert del_resp.status_code == 200, del_resp.text

    after = (await client.get("/api/v1/dashboard")).json()["data"]
    assert after["stats"]["total_scans"] == 1
    verdict_total_after = (
        after["stats"]["ai_detected"] + after["stats"]["human_verified"] + after["stats"]["uncertain"]
    )
    # This is the exact invariant that broke: verdict counts must never
    # exceed total_scans, and after deleting one of two scans both must
    # read exactly 1 (not verdict_total_after == 2, which is what the
    # unjoined query produced).
    assert verdict_total_after == 1
    assert verdict_total_after <= after["stats"]["total_scans"]

    remaining_ids = {item["scan_id"] for item in after["recent_activity"]}
    assert remaining_ids == {kept_scan_id}
