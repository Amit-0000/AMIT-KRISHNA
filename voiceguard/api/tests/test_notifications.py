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

from api.auth import service as auth_service
from api.inference import jobs as jobs_module
from api.notifications import repository as notification_repository
from api.scans import jobs as scans_jobs_module
from api.scans import repository as scans_repository

pytestmark = pytest.mark.asyncio


def _extract_token(url: str) -> str:
    return parse_qs(urlparse(url).query)["token"][0]


@pytest.fixture
def captured_emails(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    captured: dict[str, str] = {}

    async def fake_verification_email(*, to: str, verification_url: str) -> None:
        captured["verification_url"] = verification_url

    monkeypatch.setattr(auth_service, "send_verification_email", fake_verification_email)
    return captured


async def _register_and_login(client: AsyncClient, captured_emails: dict[str, str], email: str = "notif@example.com") -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Str0ng!Pass", "display_name": "Notif Person"},
    )
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass"})


async def _get_user_id(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    import uuid

    return uuid.UUID(resp.json()["data"]["user"]["id"])


async def test_list_notifications_requires_authentication(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/notifications")
    assert resp.status_code == 401


async def test_list_notifications_empty(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_and_login(client, captured_emails)
    resp = await client.get("/api/v1/notifications")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


async def test_mark_read_and_unread_count(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession
) -> None:
    await _register_and_login(client, captured_emails)
    user_id = await _get_user_id(client)

    n1 = await notification_repository.create(
        db_session, user_id=user_id, type="scan_complete", title="Scan complete", body="hello"
    )
    await notification_repository.create(db_session, user_id=user_id, type="system", title="Update", body="world")
    await db_session.commit()

    unread_resp = await client.get("/api/v1/notifications/unread-count")
    assert unread_resp.json()["data"]["unread_count"] == 2

    read_resp = await client.patch(f"/api/v1/notifications/{n1.id}/read")
    assert read_resp.status_code == 200
    assert read_resp.json()["data"]["notification"]["read"] is True

    unread_resp2 = await client.get("/api/v1/notifications/unread-count")
    assert unread_resp2.json()["data"]["unread_count"] == 1

    mark_all_resp = await client.post("/api/v1/notifications/mark-all-read")
    assert mark_all_resp.status_code == 200

    unread_resp3 = await client.get("/api/v1/notifications/unread-count")
    assert unread_resp3.json()["data"]["unread_count"] == 0


async def test_cannot_mark_read_someone_elses_notification(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession
) -> None:
    await _register_and_login(client, captured_emails, email="owner@example.com")
    owner_id = await _get_user_id(client)
    notif = await notification_repository.create(
        db_session, user_id=owner_id, type="system", title="Secret", body="private"
    )
    await db_session.commit()

    await client.post("/api/v1/auth/logout")
    await _register_and_login(client, captured_emails, email="intruder@example.com")

    resp = await client.patch(f"/api/v1/notifications/{notif.id}/read")
    assert resp.status_code == 404


async def test_delete_notification(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession
) -> None:
    await _register_and_login(client, captured_emails)
    user_id = await _get_user_id(client)
    notif = await notification_repository.create(
        db_session, user_id=user_id, type="system", title="Bye", body="bye"
    )
    await db_session.commit()

    resp = await client.delete(f"/api/v1/notifications/{notif.id}")
    assert resp.status_code == 200

    list_resp = await client.get("/api/v1/notifications")
    assert list_resp.json()["data"] == []


def _wav_bytes(seconds: float = 1.0, rate: int = 16000, tone: int = 4000) -> bytes:
    n_frames = int(seconds * rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack("<" + "h" * n_frames, *([tone] * n_frames)))
    return buf.getvalue()


async def test_scan_completion_creates_a_notification(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession, ai_checkpoint: Path
) -> None:
    """Regression test for the "Notifications are permanently empty for
    every user" bug: notifications.repository.create() existed but nothing
    in the running app ever called it. A completed scan must produce a real,
    visible notification."""
    await _register_and_login(client, captured_emails, email="scan-notif@example.com")

    resp = await client.post("/api/v1/scans", files={"file": ("clip.wav", _wav_bytes(), "audio/wav")})
    assert resp.status_code == 201, resp.text
    scan_id = resp.json()["data"]["scan"]["id"]
    await scans_jobs_module.run_preprocessing_job(uuid.UUID(scan_id), db_session.bind)

    process_resp = await client.post(f"/api/v1/scans/{scan_id}/process")
    assert process_resp.status_code == 202, process_resp.text
    scan = await scans_repository.get_by_id(db_session, uuid.UUID(scan_id))
    await jobs_module.run_ai_pipeline_job(scan.id, db_session.bind)

    list_resp = await client.get("/api/v1/notifications")
    assert list_resp.status_code == 200
    notifications = list_resp.json()["data"]
    assert len(notifications) == 1
    assert notifications[0]["type"] == "scan_complete"
    assert notifications[0]["read"] is False
    assert scan_id in notifications[0]["action_url"]

    unread_resp = await client.get("/api/v1/notifications/unread-count")
    assert unread_resp.json()["data"]["unread_count"] == 1
