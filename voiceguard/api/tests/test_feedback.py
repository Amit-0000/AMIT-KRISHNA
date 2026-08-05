from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient

from api.auth import service as auth_service

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


async def _register_and_login(client: AsyncClient, captured_emails: dict[str, str], email: str = "fb@example.com") -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Str0ng!Pass", "display_name": "FB Person"},
    )
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass"})


async def test_submit_feedback_anonymous(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/feedback",
        json={"category": "general", "message": "This is a solid piece of feedback text.", "email": "anon@example.com"},
    )
    assert resp.status_code == 201
    body = resp.json()["data"]["feedback"]
    assert body["category"] == "general"
    assert body["user_id"] is None
    assert body["email"] == "anon@example.com"
    assert body["priority"] == "normal"


async def test_submit_feedback_authenticated_defaults_email_and_priority(
    client: AsyncClient, captured_emails: dict[str, str]
) -> None:
    await _register_and_login(client, captured_emails)
    resp = await client.post(
        "/api/v1/feedback",
        json={"category": "bug", "message": "Something broke when uploading a large file."},
    )
    assert resp.status_code == 201
    body = resp.json()["data"]["feedback"]
    assert body["user_id"] is not None
    assert body["email"] == "fb@example.com"
    assert body["priority"] == "high"


async def test_submit_feedback_rejects_invalid_category(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/feedback",
        json={"category": "not_a_real_category", "message": "1234567890"},
    )
    assert resp.status_code == 422


async def test_submit_feedback_rejects_short_message(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/feedback", json={"category": "general", "message": "short"})
    assert resp.status_code == 422


async def test_list_feedback_requires_admin(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_and_login(client, captured_emails)
    resp = await client.get("/api/v1/feedback")
    assert resp.status_code == 403


async def test_list_feedback_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/feedback")
    assert resp.status_code == 401
