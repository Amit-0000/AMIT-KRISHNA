from __future__ import annotations

import asyncio
import logging
import re
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage
from functools import lru_cache

from api.core.config import Settings, get_settings

logger = logging.getLogger("voiceguard.email")


class EmailProvider(ABC):
    @abstractmethod
    async def send(self, *, to: str, subject: str, html_body: str, text_body: str) -> None: ...


class ConsoleEmailProvider(EmailProvider):
    """Fully functional provider for local development and CI: writes the
    email to the log instead of dispatching it over SMTP. Not a stand-in —
    this is the intended EMAIL_PROVIDER=console behavior."""

    async def send(self, *, to: str, subject: str, html_body: str, text_body: str) -> None:
        # security-review.md F-15: this logs the live reset/verification token
        # (needed for local dev/CI to actually complete those flows without a
        # real mailbox — see e.g. e2e/appium's password-recovery test, which
        # deliberately reads it back from these logs). Redact it whenever the
        # environment claims to be production so a real deployment's logs
        # never carry a usable bearer token even if EMAIL_PROVIDER=console
        # were left on (validate_production() below also refuses to boot in
        # that case — this redaction is defense-in-depth, not the primary fix).
        logged_body = text_body
        if get_settings().is_production:
            logged_body = re.sub(r"([?&]token=)[^\s&]+", r"\1<redacted>", text_body)
        logger.info(
            "email_dispatched (console provider)\n--- TO: %s\n--- SUBJECT: %s\n--- BODY:\n%s",
            to,
            subject,
            logged_body,
        )


class SmtpEmailProvider(EmailProvider):
    """Generic SMTP transport, parameterized rather than reading Settings
    directly — this is what makes EMAIL_PROVIDER=resend and
    EMAIL_PROVIDER=smtp the same code path with two different connection
    profiles (see get_email_provider below) instead of two near-duplicate
    classes."""

    def __init__(
        self,
        *,
        host: str | None,
        port: int,
        username: str | None,
        password: str | None,
        use_tls: bool,
        from_address: str,
        from_name: str,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._from_address = from_address
        self._from_name = from_name

    def _send_sync(self, *, to: str, subject: str, html_body: str, text_body: str) -> None:
        message = EmailMessage()
        message["From"] = f"{self._from_name} <{self._from_address}>"
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
            if self._use_tls:
                smtp.starttls()
            if self._username and self._password:
                smtp.login(self._username, self._password)
            smtp.send_message(message)

    async def send(self, *, to: str, subject: str, html_body: str, text_body: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self._send_sync(to=to, subject=subject, html_body=html_body, text_body=text_body))


def _build_provider(settings: Settings) -> EmailProvider:
    if settings.EMAIL_PROVIDER == "resend":
        return SmtpEmailProvider(
            host=settings.RESEND_SMTP_HOST,
            port=settings.RESEND_SMTP_PORT,
            username="resend",
            password=settings.RESEND_API_KEY,
            use_tls=True,
            from_address=settings.EMAIL_FROM_ADDRESS,
            from_name=settings.EMAIL_FROM_NAME,
        )
    if settings.EMAIL_PROVIDER == "smtp":
        return SmtpEmailProvider(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_USE_TLS,
            from_address=settings.EMAIL_FROM_ADDRESS,
            from_name=settings.EMAIL_FROM_NAME,
        )
    return ConsoleEmailProvider()


@lru_cache
def get_email_provider() -> EmailProvider:
    return _build_provider(get_settings())


def _wrap_html(title: str, body_html: str) -> str:
    return f"""<!doctype html>
<html><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#0B0B18;color:#F0F0FF;padding:32px;">
  <div style="max-width:480px;margin:0 auto;background:#141428;border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:32px;">
    <h1 style="font-size:18px;margin:0 0 16px;">{title}</h1>
    {body_html}
    <p style="margin-top:32px;font-size:12px;color:#8888A8;">VoiceGuard &mdash; AI-powered audio deepfake detection.</p>
  </div>
</body></html>"""


async def try_send_verification_email(*, to: str, verification_url: str) -> bool:
    """Best-effort wrapper for the registration/resend-verification paths:
    the caller is expected to have already durably committed the user and
    verification-token rows *before* calling this, so a provider outage
    here (e.g. Resend's sandbox-sender rejecting a non-owner recipient)
    degrades to "email not sent yet, retry via resend-verification" instead
    of failing the whole request and rolling back an account that was
    otherwise created successfully. Returns False rather than raising —
    callers must not let SMTP/provider exception details reach the client
    (they can contain provider-specific diagnostics, not secrets, but are
    still not something the frontend should render or a client should see)."""
    try:
        await send_verification_email(to=to, verification_url=verification_url)
        return True
    except Exception as exc:  # noqa: BLE001 - any provider failure must degrade, not crash the request
        logger.error("verification_email_send_failed", extra={"error_type": type(exc).__name__, "error": str(exc)})
        return False


async def send_verification_email(*, to: str, verification_url: str) -> None:
    provider = get_email_provider()
    html = _wrap_html(
        "Verify your email",
        f'<p>Thanks for signing up for VoiceGuard. Confirm your email address to activate your account:</p>'
        f'<p><a href="{verification_url}" style="color:#7C5CFF;">Verify email address</a></p>'
        f'<p style="font-size:12px;color:#8888A8;">This link expires in 24 hours.</p>',
    )
    text = f"Verify your VoiceGuard account: {verification_url}\nThis link expires in 24 hours."
    await provider.send(to=to, subject="Verify your VoiceGuard email", html_body=html, text_body=text)


async def try_send_password_reset_email(*, to: str, reset_url: str) -> bool:
    """Same reasoning as try_send_verification_email: the caller must have
    already durably committed the reset-token row before calling this."""
    try:
        await send_password_reset_email(to=to, reset_url=reset_url)
        return True
    except Exception as exc:  # noqa: BLE001 - any provider failure must degrade, not crash the request
        logger.error("password_reset_email_send_failed", extra={"error_type": type(exc).__name__, "error": str(exc)})
        return False


async def send_password_reset_email(*, to: str, reset_url: str) -> None:
    provider = get_email_provider()
    html = _wrap_html(
        "Reset your password",
        f'<p>We received a request to reset your VoiceGuard password.</p>'
        f'<p><a href="{reset_url}" style="color:#7C5CFF;">Reset password</a></p>'
        f'<p style="font-size:12px;color:#8888A8;">This link expires in 1 hour. If you did not request this, you can ignore this email.</p>',
    )
    text = f"Reset your VoiceGuard password: {reset_url}\nThis link expires in 1 hour."
    await provider.send(to=to, subject="Reset your VoiceGuard password", html_body=html, text_body=text)


async def send_password_changed_email(*, to: str) -> None:
    provider = get_email_provider()
    html = _wrap_html(
        "Your password was changed",
        '<p>This is a confirmation that the password for your VoiceGuard account was just changed. '
        "If you didn't make this change, please reset your password immediately and contact support.</p>",
    )
    text = "Your VoiceGuard password was just changed. If this wasn't you, reset your password immediately."
    await provider.send(to=to, subject="Your VoiceGuard password was changed", html_body=html, text_body=text)
