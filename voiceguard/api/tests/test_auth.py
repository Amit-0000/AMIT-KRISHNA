from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import service as auth_service
from api.core.audit import AuditEventType, AuditLog

pytestmark = pytest.mark.asyncio


def _extract_token(url: str) -> str:
    return parse_qs(urlparse(url).query)["token"][0]


@pytest.fixture
def captured_emails(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    captured: dict[str, str] = {}

    async def fake_verification_email(*, to: str, verification_url: str) -> None:
        captured["verification_url"] = verification_url

    async def fake_reset_email(*, to: str, reset_url: str) -> None:
        captured["reset_url"] = reset_url

    async def fake_changed_email(*, to: str) -> None:
        captured["password_changed_to"] = to

    monkeypatch.setattr(auth_service, "send_verification_email", fake_verification_email)
    monkeypatch.setattr(auth_service, "send_password_reset_email", fake_reset_email)
    monkeypatch.setattr(auth_service, "send_password_changed_email", fake_changed_email)
    return captured


async def _register(client: AsyncClient, email: str = "person@example.com", password: str = "Str0ng!Pass") -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Person One"},
    )
    assert resp.status_code == 201, resp.text


async def test_register_success(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register(client)
    assert "verification_url" in captured_emails


async def test_register_duplicate_email_conflicts(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "person@example.com", "password": "Str0ng!Pass", "display_name": "Dup"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


async def test_register_weak_password_rejected(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "weak", "display_name": "Weak"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_PASSWORD"


async def test_login_before_verification_returns_403(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register(client)
    resp = await client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": "Str0ng!Pass"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"


async def test_login_wrong_password_returns_401(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register(client)
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    resp = await client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": "WrongPass1!"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_unknown_email_returns_401_not_404(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    resp = await client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "WhoKnows1!"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_failure_audit_log_survives_session_rollback(
    client: AsyncClient, captured_emails: dict[str, str], db_session: AsyncSession
) -> None:
    # login_user() writes a LOGIN_FAILURE audit row and then raises
    # InvalidCredentialsError, which api.core.database.get_db turns into a
    # rollback of the request's own session. The audit row must still be
    # there afterwards — it's committed on its own session (see
    # api.core.audit.write_audit_log), independent of that rollback.
    await _register(client)
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    resp = await client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": "WrongPass1!"})
    assert resp.status_code == 401

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.event_type == AuditEventType.LOGIN_FAILURE.value)
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].details == {"reason": "invalid_credentials"}


async def test_full_register_verify_login_me_refresh_logout_flow(
    client: AsyncClient, captured_emails: dict[str, str]
) -> None:
    await _register(client)
    token = _extract_token(captured_emails["verification_url"])

    verify_resp = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verify_resp.status_code == 200
    assert verify_resp.json()["data"]["user"]["email_verified"] is True

    login_resp = await client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": "Str0ng!Pass"})
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.cookies
    assert "refresh_token" in login_resp.cookies

    me_resp = await client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["user"]["email"] == "person@example.com"
    assert me_resp.json()["data"]["user"]["onboarding_completed"] is True

    refresh_resp = await client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.cookies

    logout_resp = await client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200

    me_after_logout = await client.get("/api/v1/auth/me")
    assert me_after_logout.status_code == 401


async def test_logout_revokes_refresh_token_server_side(
    client: AsyncClient, captured_emails: dict[str, str]
) -> None:
    # The refresh cookie must be scoped so it's actually sent to POST
    # /api/v1/auth/logout (previously Path=/api/v1/auth/refresh, a sibling
    # path no spec-compliant client ever sends there — logout cleared cookies
    # client-side but never actually revoked the token server-side).
    await _register(client)
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    await client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": "Str0ng!Pass"})

    refresh_token_value = client.cookies.get("refresh_token")
    assert refresh_token_value

    logout_resp = await client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200

    # Present the pre-logout refresh token explicitly — proves it's dead
    # server-side, not merely dropped from the client's own cookie jar.
    client.cookies.set("refresh_token", refresh_token_value)
    reuse_resp = await client.post("/api/v1/auth/refresh")
    assert reuse_resp.status_code == 401
    assert reuse_resp.json()["error"]["code"] == "SESSION_EXPIRED"


async def test_refresh_token_reuse_revokes_all_sessions(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register(client)
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    await client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": "Str0ng!Pass"})

    stolen_refresh_token = client.cookies.get("refresh_token")
    assert stolen_refresh_token

    first_rotation = await client.post("/api/v1/auth/refresh")
    assert first_rotation.status_code == 200

    # Replay the now-revoked (rotated-away) refresh token — this must be
    # detected as reuse and nuke every session for the user.
    client.cookies.set("refresh_token", stolen_refresh_token)
    replay_resp = await client.post("/api/v1/auth/refresh")
    assert replay_resp.status_code == 401
    assert replay_resp.json()["error"]["code"] == "SESSION_EXPIRED"

    # Even the legitimately-rotated token from first_rotation must now be dead.
    client.cookies.set("refresh_token", first_rotation.cookies.get("refresh_token"))
    second_replay = await client.post("/api/v1/auth/refresh")
    assert second_replay.status_code == 401


async def test_forgot_password_always_returns_success(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    resp = await client.post("/api/v1/auth/forgot-password", json={"email": "nonexistent@example.com"})
    assert resp.status_code == 200
    assert "reset_url" not in captured_emails  # no email sent for unknown address

    await _register(client)
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    resp2 = await client.post("/api/v1/auth/forgot-password", json={"email": "person@example.com"})
    assert resp2.status_code == 200
    assert "reset_url" in captured_emails


async def test_reset_password_and_relogin(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    await _register(client)
    verify_token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": verify_token})

    await client.post("/api/v1/auth/forgot-password", json={"email": "person@example.com"})
    reset_token = _extract_token(captured_emails["reset_url"])

    reset_resp = await client.post(
        "/api/v1/auth/reset-password", json={"token": reset_token, "password": "NewStr0ng!Pass"}
    )
    assert reset_resp.status_code == 200

    old_login = await client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": "Str0ng!Pass"})
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login", json={"email": "person@example.com", "password": "NewStr0ng!Pass"}
    )
    assert new_login.status_code == 200


async def test_register_rate_limit_enforced(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    for i in range(5):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": f"user{i}@example.com", "password": "Str0ng!Pass", "display_name": "Bulk"},
        )
        assert resp.status_code == 201

    over_limit = await client.post(
        "/api/v1/auth/register",
        json={"email": "user_over_limit@example.com", "password": "Str0ng!Pass", "display_name": "Over"},
    )
    assert over_limit.status_code == 429
    assert over_limit.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Retry-After" in over_limit.headers
