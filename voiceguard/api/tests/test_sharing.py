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
    from api.core import email as email_service

    captured: dict[str, str] = {}

    async def fake_verification_email(*, to: str, verification_url: str) -> None:
        captured["verification_url"] = verification_url

    monkeypatch.setattr(email_service, "send_verification_email", fake_verification_email)
    return captured


async def _register_verify_login(client: AsyncClient, captured_emails: dict[str, str], *, email: str) -> None:
    await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "Str0ng!Pass", "display_name": "Tester"}
    )
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass"})


async def _complete_scan(client: AsyncClient, db_session: AsyncSession) -> str:
    resp = await client.post("/api/v1/scans", files={"file": ("clip.wav", _wav_bytes(), "audio/wav")})
    assert resp.status_code == 201, resp.text
    scan_id = resp.json()["data"]["scan"]["id"]
    await scans_jobs_module.run_preprocessing_job(uuid.UUID(scan_id), db_session.bind)

    process_resp = await client.post(f"/api/v1/scans/{scan_id}/process")
    assert process_resp.status_code == 202, process_resp.text
    scan = await scans_repository.get_by_id(db_session, uuid.UUID(scan_id))
    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)
    return scan_id


async def test_share_requires_authentication(client: AsyncClient) -> None:
    resp = await client.post(f"/api/v1/scans/{uuid.uuid4()}/share")
    assert resp.status_code == 401


async def test_share_rejects_scan_without_result(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails, email="noresult@example.com")
    upload = await client.post("/api/v1/scans", files={"file": ("clip.wav", _wav_bytes(), "audio/wav")})
    scan_id = upload.json()["data"]["scan"]["id"]

    resp = await client.post(f"/api/v1/scans/{scan_id}/share")
    assert resp.status_code == 422


async def test_create_and_fetch_shared_result(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, ai_checkpoint: Path
) -> None:
    await _register_verify_login(client, captured_emails, email="sharer@example.com")
    scan_id = await _complete_scan(client, db_session)

    share_resp = await client.post(f"/api/v1/scans/{scan_id}/share")
    assert share_resp.status_code == 200, share_resp.text
    share_url = share_resp.json()["data"]["share_url"]
    token = share_resp.json()["data"]["token"]
    assert token in share_url

    # Creating a second share while one is already active returns the same token.
    share_resp2 = await client.post(f"/api/v1/scans/{scan_id}/share")
    assert share_resp2.json()["data"]["token"] == token

    public_resp = await client.get(f"/api/v1/scans/shared/{token}")
    assert public_resp.status_code == 200
    assert public_resp.json()["data"]["result"]["scan_id"] == scan_id


async def test_shared_result_unknown_token_is_404(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/scans/shared/not-a-real-token")
    assert resp.status_code == 404


async def test_revoke_share_makes_token_inactive(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, ai_checkpoint: Path
) -> None:
    await _register_verify_login(client, captured_emails, email="revoker@example.com")
    scan_id = await _complete_scan(client, db_session)

    share_resp = await client.post(f"/api/v1/scans/{scan_id}/share")
    token = share_resp.json()["data"]["token"]

    revoke_resp = await client.delete(f"/api/v1/scans/{scan_id}/share")
    assert revoke_resp.status_code == 200

    public_resp = await client.get(f"/api/v1/scans/shared/{token}")
    assert public_resp.status_code == 404

    revoke_again = await client.delete(f"/api/v1/scans/{scan_id}/share")
    assert revoke_again.status_code == 404


async def test_share_owner_only(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, ai_checkpoint: Path
) -> None:
    await _register_verify_login(client, captured_emails, email="owner2@example.com")
    scan_id = await _complete_scan(client, db_session)

    await client.post("/api/v1/auth/logout")
    captured_emails.clear()
    await _register_verify_login(client, captured_emails, email="intruder2@example.com")

    resp = await client.post(f"/api/v1/scans/{scan_id}/share")
    assert resp.status_code == 404
