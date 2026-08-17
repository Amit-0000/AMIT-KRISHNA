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

    async def fake_changed_email(*, to: str) -> None:
        captured["password_changed_to"] = to

    from api.core import email as email_service

    # send_verification_email is now called from api.core.email.try_send_verification_email
    # (a same-module bare-name call), so it must be patched on that module, not auth_service.
    monkeypatch.setattr(email_service, "send_verification_email", fake_verification_email)
    monkeypatch.setattr(auth_service, "send_password_changed_email", fake_changed_email)
    return captured


async def _register_verify_login(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "profile@example.com", "password": "Str0ng!Pass", "display_name": "Profile Person"},
    )
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    await client.post("/api/v1/auth/login", json={"email": "profile@example.com", "password": "Str0ng!Pass"})


async def test_profile_requires_authentication(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/user/profile")
    assert resp.status_code == 401


async def test_get_and_update_profile(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails)

    get_resp = await client.get("/api/v1/user/profile")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["user"]["display_name"] == "Profile Person"

    patch_resp = await client.patch("/api/v1/user/profile", json={"display_name": "New Name"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["user"]["display_name"] == "New Name"


async def test_change_password_wrong_current_password(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails)

    resp = await client.post(
        "/api/v1/user/change-password",
        json={"current_password": "WrongOne1!", "new_password": "AnotherStr0ng!"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_profile_reflects_real_scan_count_today(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails)

    zero_resp = await client.get("/api/v1/user/profile")
    assert zero_resp.json()["data"]["user"]["scan_count_today"] == 0

    await client.post(
        "/api/v1/scans", files={"file": ("clip.wav", b"RIFF" + b"\x00" * 100, "audio/wav")}
    )

    one_resp = await client.get("/api/v1/user/profile")
    assert one_resp.json()["data"]["user"]["scan_count_today"] == 1


async def test_update_profile_persists_onboarding_completed(
    client: AsyncClient, captured_emails: dict[str, str]
) -> None:
    await _register_verify_login(client, captured_emails)

    patch_resp = await client.patch("/api/v1/user/profile", json={"onboarding_completed": False})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["user"]["onboarding_completed"] is False

    get_resp = await client.get("/api/v1/user/profile")
    assert get_resp.json()["data"]["user"]["onboarding_completed"] is False


async def test_change_password_success_revokes_session(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register_verify_login(client, captured_emails)

    resp = await client.post(
        "/api/v1/user/change-password",
        json={"current_password": "Str0ng!Pass", "new_password": "AnotherStr0ng!"},
    )
    assert resp.status_code == 200
    assert captured_emails.get("password_changed_to") == "profile@example.com"

    old_login = await client.post(
        "/api/v1/auth/login", json={"email": "profile@example.com", "password": "Str0ng!Pass"}
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login", json={"email": "profile@example.com", "password": "AnotherStr0ng!"}
    )
    assert new_login.status_code == 200
