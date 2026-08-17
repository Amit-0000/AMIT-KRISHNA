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

    from api.core import email as email_service

    # send_verification_email / send_password_reset_email are now called from
    # api.core.email's try_send_* wrappers (same-module bare-name calls), so
    # they must be patched on that module, not auth_service.
    # send_password_changed_email is still called directly from auth_service,
    # so it stays patched there.
    monkeypatch.setattr(email_service, "send_verification_email", fake_verification_email)
    monkeypatch.setattr(email_service, "send_password_reset_email", fake_reset_email)
    monkeypatch.setattr(auth_service, "send_password_changed_email", fake_changed_email)
    return captured


async def _register(client: AsyncClient, email: str = "person@example.com", password: str = "Str0ng!Pass") -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Person One"},
    )
    assert resp.status_code == 201, resp.text


async def test_register_success(client: AsyncClient, captured_emails: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "person@example.com", "password": "Str0ng!Pass", "display_name": "Person One"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["email_delivery"] == "sent"
    assert "verification_url" in captured_emails


async def test_register_email_provider_failure_does_not_roll_back(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
) -> None:
    """Production diagnostic 2026-08-15: Resend's sandbox sender rejects any
    recipient but the account owner with SMTP 550, which used to raise out
    of register_user() and roll back the just-created account via
    api.core.database.get_db's rollback-on-exception, turning a delivery
    problem into a total registration failure. register_user() now commits
    the user + verification token before attempting the email, so the
    account must survive an email-provider outage — this proves it end to
    end, including that the token committed before the failed send is
    still valid and usable."""
    from api.core import email as email_service
    from api.user.models import User

    captured: dict[str, str] = {}

    async def failing_verification_email(*, to: str, verification_url: str) -> None:
        captured["verification_url"] = verification_url
        raise ConnectionRefusedError("simulated SMTP provider outage — smtp.resend.com:2587 unreachable")

    monkeypatch.setattr(email_service, "send_verification_email", failing_verification_email)

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "emailfail@example.com", "password": "Str0ng!Pass", "display_name": "Email Fail"},
    )

    # (b) registration does NOT roll back — still a clean success, not a 500
    assert resp.status_code == 201, resp.text
    body = resp.json()["data"]
    assert body["email_delivery"] == "failed"

    # (c) user remains unverified
    assert body["user"]["email_verified"] is False

    # (e) the provider's exception text never reaches the client
    assert "simulated SMTP provider outage" not in resp.text
    assert "ConnectionRefusedError" not in resp.text
    assert "smtp.resend.com" not in resp.text

    # (b) continued — the user row genuinely persisted (this session's own
    # query, independent of whatever session the request used)
    result = await db_session.execute(select(User).where(User.email == "emailfail@example.com"))
    user = result.scalar_one()
    assert user.email_verified is False

    # (d) the verification token committed before the failed send is still
    # valid and usable — proves the token isn't silently invalidated or lost
    assert "verification_url" in captured
    token = _extract_token(captured["verification_url"])
    verify_resp = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verify_resp.status_code == 200, verify_resp.text
    assert verify_resp.json()["data"]["user"]["email_verified"] is True


async def test_resend_verification_recovers_after_initial_email_failure(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Requirement: a user whose registration email failed to send must be
    able to use POST /auth/resend-verification to get a working link. Also
    covers /auth/resend-verification itself, which had no test coverage
    before this change."""
    from api.core import email as email_service

    async def failing_verification_email(*, to: str, verification_url: str) -> None:
        raise ConnectionRefusedError("simulated SMTP provider outage")

    monkeypatch.setattr(email_service, "send_verification_email", failing_verification_email)

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "retryme@example.com", "password": "Str0ng!Pass", "display_name": "Retry Me"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["email_delivery"] == "failed"

    captured: dict[str, str] = {}

    async def working_verification_email(*, to: str, verification_url: str) -> None:
        captured["verification_url"] = verification_url

    monkeypatch.setattr(email_service, "send_verification_email", working_verification_email)

    resend_resp = await client.post("/api/v1/auth/resend-verification", json={"email": "retryme@example.com"})
    assert resend_resp.status_code == 200, resend_resp.text
    # enumeration-resistant response shape — must not vary with what happened
    assert resend_resp.json()["data"] == {}
    assert "verification_url" in captured

    token = _extract_token(captured["verification_url"])
    verify_resp = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verify_resp.status_code == 200, verify_resp.text
    assert verify_resp.json()["data"]["user"]["email_verified"] is True


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


async def test_mobile_client_gets_bearer_tokens_and_can_authenticate_without_cookies(
    client: AsyncClient, captured_emails: dict[str, str]
) -> None:
    """The Capacitor Android app's WebView origin (https://localhost) is
    cross-site from this API's perspective, so SameSite=Strict cookies never
    come back on its later requests even though login sets them. Confirms
    the additive bearer-token path: origin=https://localhost gets raw tokens
    in the body, and a request with only Authorization (no cookies at all)
    still authenticates and can refresh/logout via a body-supplied token."""
    await _register(client)
    token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "Str0ng!Pass"},
        headers={"origin": "https://localhost"},
    )
    assert login_resp.status_code == 200
    body = login_resp.json()["data"]
    access_token = body["access_token"]
    refresh_token = body["refresh_token"]
    assert access_token and refresh_token

    # A non-mobile-origin login must NOT get raw tokens in the body — only
    # the cookie flow, unchanged.
    other_login = await client.post(
        "/api/v1/auth/login", json={"email": "person@example.com", "password": "Str0ng!Pass"}
    )
    assert "access_token" not in other_login.json()["data"]

    client.cookies.clear()
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["user"]["email"] == "person@example.com"

    # No cookies, no Authorization header at all -> unauthenticated.
    assert (await client.get("/api/v1/auth/me")).status_code == 401

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
        headers={"origin": "https://localhost"},
    )
    assert refresh_resp.status_code == 200
    new_access = refresh_resp.json()["data"]["access_token"]
    assert new_access and new_access != access_token

    logout_resp = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 200

    # The refresh token logout revoked was already rotated by the refresh
    # call above, so this just confirms logout didn't error without cookies
    # to fall back on — reuse-detection behavior is covered by
    # test_refresh_token_reuse_revokes_all_sessions.


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


async def test_forgot_password_email_failure_does_not_break_reset_token(
    client: AsyncClient, captured_emails: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """forgot_password() had the same commit-after-send bug register_user()
    was fixed for on 2026-08-15 — the reset-token row would roll back along
    with a failed send. Fixed the same way (commit before send); this proves
    the token survives a provider outage and is still usable."""
    await _register(client)
    verify_token = _extract_token(captured_emails["verification_url"])
    await client.post("/api/v1/auth/verify-email", json={"token": verify_token})

    from api.core import email as email_service

    captured: dict[str, str] = {}

    async def failing_reset_email(*, to: str, reset_url: str) -> None:
        captured["reset_url"] = reset_url
        raise ConnectionRefusedError("simulated SMTP provider outage")

    monkeypatch.setattr(email_service, "send_password_reset_email", failing_reset_email)

    resp = await client.post("/api/v1/auth/forgot-password", json={"email": "person@example.com"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == {}
    assert "simulated SMTP provider outage" not in resp.text

    reset_token = _extract_token(captured["reset_url"])
    reset_resp = await client.post(
        "/api/v1/auth/reset-password", json={"token": reset_token, "password": "NewStr0ng!Pass"}
    )
    assert reset_resp.status_code == 200, reset_resp.text

    new_login = await client.post(
        "/api/v1/auth/login", json={"email": "person@example.com", "password": "NewStr0ng!Pass"}
    )
    assert new_login.status_code == 200


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
