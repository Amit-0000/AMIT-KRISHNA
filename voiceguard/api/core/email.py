from __future__ import annotations

import asyncio
import logging
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
        logger.info(
            "email_dispatched (console provider)\n--- TO: %s\n--- SUBJECT: %s\n--- BODY:\n%s",
            to,
            subject,
            text_body,
        )


class SmtpEmailProvider(EmailProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _send_sync(self, *, to: str, subject: str, html_body: str, text_body: str) -> None:
        settings = self._settings
        message = EmailMessage()
        message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            if settings.SMTP_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)

    async def send(self, *, to: str, subject: str, html_body: str, text_body: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self._send_sync(to=to, subject=subject, html_body=html_body, text_body=text_body))


@lru_cache
def get_email_provider() -> EmailProvider:
    settings = get_settings()
    if settings.EMAIL_PROVIDER == "smtp":
        return SmtpEmailProvider(settings)
    return ConsoleEmailProvider()


def _wrap_html(title: str, body_html: str) -> str:
    return f"""<!doctype html>
<html><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#0B0B18;color:#F0F0FF;padding:32px;">
  <div style="max-width:480px;margin:0 auto;background:#141428;border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:32px;">
    <h1 style="font-size:18px;margin:0 0 16px;">{title}</h1>
    {body_html}
    <p style="margin-top:32px;font-size:12px;color:#8888A8;">VoiceGuard &mdash; AI-powered audio deepfake detection.</p>
  </div>
</body></html>"""


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
