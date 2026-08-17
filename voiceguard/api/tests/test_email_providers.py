"""Provider-level tests for api.core.email — exercises the real SMTP
transport (via a fake smtplib.SMTP, not the higher-level monkeypatches
other test files use to bypass it) and the resend/smtp provider dispatch
added by the 2026-08-15 SMTP-provider migration.
"""
from __future__ import annotations

import pytest

from api.core import email as email_module
from api.core.config import Settings

pytestmark = pytest.mark.asyncio


def _fake_smtp_class(captured: dict) -> type:
    class FakeSMTP:
        def __init__(self, host, port, timeout=10):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def starttls(self):
            captured["starttls_called"] = True

        def login(self, username, password):
            captured["login_username"] = username
            captured["login_password"] = password

        def send_message(self, message):
            captured["from"] = str(message["From"])
            captured["to"] = str(message["To"])
            captured["subject"] = str(message["Subject"])

    return FakeSMTP


async def test_smtp_provider_sends_via_real_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    """(1) SMTP email successfully sends — proves the actual SmtpEmailProvider
    transport (connect, STARTTLS, login, send_message), not just that some
    higher-level function was called."""
    captured: dict = {}
    monkeypatch.setattr(email_module.smtplib, "SMTP", _fake_smtp_class(captured))

    provider = email_module.SmtpEmailProvider(
        host="mail.example.com",
        port=587,
        username="notifications@example.com",
        password="s3cr3t-app-password",
        use_tls=True,
        from_address="notifications@example.com",
        from_name="VoiceGuard",
    )
    await provider.send(to="user@example.com", subject="Hi", html_body="<p>hi</p>", text_body="hi")

    assert captured["host"] == "mail.example.com"
    assert captured["port"] == 587
    assert captured["starttls_called"] is True
    assert captured["login_username"] == "notifications@example.com"
    assert captured["login_password"] == "s3cr3t-app-password"
    assert captured["to"] == "user@example.com"
    assert captured["subject"] == "Hi"
    assert "notifications@example.com" in captured["from"]


async def test_smtp_provider_selected_when_email_provider_is_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    """(10) SMTP provider works when EMAIL_PROVIDER=smtp — verifies
    get_email_provider's dispatch actually builds a SmtpEmailProvider wired
    to the generic SMTP_* settings, not the Resend ones."""
    captured: dict = {}
    monkeypatch.setattr(email_module.smtplib, "SMTP", _fake_smtp_class(captured))

    settings = Settings(
        EMAIL_PROVIDER="smtp",
        SMTP_HOST="mail.example.com",
        SMTP_PORT=465,
        SMTP_USERNAME="notifications@example.com",
        SMTP_PASSWORD="s3cr3t-app-password",
        SMTP_USE_TLS=False,
        EMAIL_FROM_ADDRESS="notifications@example.com",
        EMAIL_FROM_NAME="VoiceGuard",
    )
    provider = email_module._build_provider(settings)
    assert isinstance(provider, email_module.SmtpEmailProvider)

    await provider.send(to="user@example.com", subject="Hi", html_body="<p>hi</p>", text_body="hi")
    assert captured["host"] == "mail.example.com"
    assert captured["port"] == 465
    assert "starttls_called" not in captured  # SMTP_USE_TLS=False


async def test_smtp_provider_skips_auth_for_unauthenticated_relay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mailpit (docker-compose's dev SMTP capture service) requires no auth
    and its config sets SMTP_USERNAME/SMTP_PASSWORD to empty strings, not
    unset — proves that shape (not just None) still skips smtp.login()."""
    captured: dict = {}
    monkeypatch.setattr(email_module.smtplib, "SMTP", _fake_smtp_class(captured))

    settings = Settings(
        EMAIL_PROVIDER="smtp",
        SMTP_HOST="mailpit",
        SMTP_PORT=1025,
        SMTP_USERNAME="",
        SMTP_PASSWORD="",
        SMTP_USE_TLS=False,
        EMAIL_FROM_ADDRESS="noreply@voiceguard.local",
        EMAIL_FROM_NAME="VoiceGuard",
    )
    provider = email_module._build_provider(settings)
    await provider.send(to="user@example.com", subject="Hi", html_body="<p>hi</p>", text_body="hi")

    assert captured["host"] == "mailpit"
    assert captured["port"] == 1025
    assert "starttls_called" not in captured
    assert "login_username" not in captured


async def test_resend_provider_selected_when_email_provider_is_resend(monkeypatch: pytest.MonkeyPatch) -> None:
    """(9) Resend provider still works when EMAIL_PROVIDER=resend — verifies
    the dispatch builds a SmtpEmailProvider wired to Resend's fixed
    connection profile (smtp.resend.com:2587, username "resend") using only
    RESEND_API_KEY, independent of whatever SMTP_* is currently set."""
    captured: dict = {}
    monkeypatch.setattr(email_module.smtplib, "SMTP", _fake_smtp_class(captured))

    settings = Settings(
        EMAIL_PROVIDER="resend",
        RESEND_API_KEY="re_test_key_not_a_real_secret",
        EMAIL_FROM_ADDRESS="onboarding@resend.dev",
        EMAIL_FROM_NAME="VoiceGuard",
        # Deliberately set SMTP_* to something else to prove resend doesn't
        # accidentally read from the generic SMTP settings.
        SMTP_HOST="should-not-be-used.example.com",
        SMTP_USERNAME="should-not-be-used",
    )
    provider = email_module._build_provider(settings)
    assert isinstance(provider, email_module.SmtpEmailProvider)

    await provider.send(to="user@example.com", subject="Hi", html_body="<p>hi</p>", text_body="hi")
    assert captured["host"] == "smtp.resend.com"
    assert captured["port"] == 2587
    assert captured["login_username"] == "resend"
    assert captured["login_password"] == "re_test_key_not_a_real_secret"


async def test_smtp_credentials_never_appear_in_logs(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """(8) SMTP credentials never appear in logs — a provider failure must
    log enough to diagnose it (exception type/message) without ever
    including the password the provider was configured with. The captured
    login() args below prove the real SmtpEmailProvider code path was
    actually exercised (password did reach smtplib), not just that a
    generic exception was raised somewhere unrelated."""
    import smtplib as real_smtplib

    login_calls: list[tuple[str, str]] = []

    class ExplodingSMTP:
        def __init__(self, host, port, timeout=10):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def starttls(self):
            pass

        def login(self, username, password):
            login_calls.append((username, password))
            raise real_smtplib.SMTPAuthenticationError(535, b"5.7.8 Authentication failed")

        def send_message(self, message):
            pass

    monkeypatch.setattr(email_module.smtplib, "SMTP", ExplodingSMTP)

    settings = Settings(
        EMAIL_PROVIDER="smtp",
        SMTP_HOST="mail.example.com",
        SMTP_PORT=587,
        SMTP_USERNAME="notifications@example.com",
        SMTP_PASSWORD="s3cr3t-app-password-must-not-leak",
        SMTP_USE_TLS=True,
        EMAIL_FROM_ADDRESS="notifications@example.com",
        EMAIL_FROM_NAME="VoiceGuard",
    )
    monkeypatch.setattr(email_module, "get_email_provider", lambda: email_module._build_provider(settings))

    with caplog.at_level("ERROR", logger="voiceguard.email"):
        sent = await email_module.try_send_verification_email(
            to="user@example.com", verification_url="https://example.com/verify-email?token=abc123"
        )

    assert sent is False
    assert login_calls == [("notifications@example.com", "s3cr3t-app-password-must-not-leak")]  # proves the real path ran
    assert "s3cr3t-app-password-must-not-leak" not in caplog.text