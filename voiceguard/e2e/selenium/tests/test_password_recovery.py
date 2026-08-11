"""Desktop password-recovery coverage (/forgot-password, /reset-password,
both GuestGuard-protected).

Full happy-path token verification is out of reach here — resetPassword's
success path needs a real token minted by the backend and delivered by
email, which only automated_test/setup_env.py's docker-logs grep can pull
out, and that mechanism is reserved for the DAST suite. What IS covered for
real: every client-renderable state of both pages, plus the real backend
rejection of a garbage token (a genuine round trip, not a fabricated one).
"""
from __future__ import annotations

import pytest

from data.test_inputs import INVALID_EMAILS, MISMATCHED_PASSWORD, WEAK_PASSWORDS
from data.users import VALID_SIGNUP_PASSWORD
from pages.auth_pages import ForgotPasswordPage, ResetPasswordPage

pytestmark = [pytest.mark.high]


def test_forgot_password_page_renders(unauthenticated_driver, base_url):
    page = ForgotPasswordPage(unauthenticated_driver, base_url)
    page.open()
    assert page.is_visible(*page.EMAIL)


def test_forgot_password_empty_submit_blocked(unauthenticated_driver, base_url):
    page = ForgotPasswordPage(unauthenticated_driver, base_url)
    page.open()
    page.submit()
    assert "/forgot-password" in page.current_url


@pytest.mark.parametrize("invalid_email", INVALID_EMAILS)
def test_forgot_password_invalid_email_blocked(unauthenticated_driver, base_url, invalid_email):
    page = ForgotPasswordPage(unauthenticated_driver, base_url)
    page.open()
    page.fill_id("email", invalid_email)
    page.submit()
    assert "/forgot-password" in page.current_url


def test_forgot_password_submit_shows_check_email(unauthenticated_driver, base_url):
    # Anti-enumeration: the backend never reveals whether the address is
    # registered (frontend/src/pages/ForgotPassword/index.tsx's onSubmit
    # comment), so this succeeds identically for any well-formed email.
    page = ForgotPasswordPage(unauthenticated_driver, base_url)
    page.open()
    page.submit_email("selenium.forgot@example.com")
    assert page.check_email_message_shown()


def test_reset_password_no_token_shows_invalid_link(unauthenticated_driver, base_url):
    page = ResetPasswordPage(unauthenticated_driver, base_url)
    page.open(token=None)
    assert page.shows_invalid_link()


def test_reset_password_form_shown_when_token_present(unauthenticated_driver, base_url):
    page = ResetPasswordPage(unauthenticated_driver, base_url)
    page.open(token="any-nonempty-token-value")
    assert page.shows_form()


def test_reset_password_rejects_mismatched_passwords(unauthenticated_driver, base_url):
    page = ResetPasswordPage(unauthenticated_driver, base_url)
    page.open(token="any-nonempty-token-value")
    page.fill_and_submit(VALID_SIGNUP_PASSWORD, MISMATCHED_PASSWORD)
    assert "match" in page.body_text().lower()


@pytest.mark.parametrize("rule", sorted(WEAK_PASSWORDS))
def test_reset_password_rejects_weak_password(unauthenticated_driver, base_url, rule):
    page = ResetPasswordPage(unauthenticated_driver, base_url)
    page.open(token="any-nonempty-token-value")
    weak = WEAK_PASSWORDS[rule]
    page.fill_and_submit(weak, weak)
    assert page.shows_form(), f"weak password ({rule}) must not be accepted and navigate off the form"


def test_reset_password_garbage_token_rejected_by_backend(unauthenticated_driver, base_url):
    page = ResetPasswordPage(unauthenticated_driver, base_url)
    page.open(token="0" * 64)
    page.fill_and_submit(VALID_SIGNUP_PASSWORD, VALID_SIGNUP_PASSWORD)
    assert page.shows_invalid_link()


def test_reset_password_field_uses_password_input_type(unauthenticated_driver, base_url):
    page = ResetPasswordPage(unauthenticated_driver, base_url)
    page.open(token="any-nonempty-token-value")
    assert page.find(*page.PASSWORD).get_attribute("type") == "password"


def test_forgot_password_email_field_uses_email_input_type(unauthenticated_driver, base_url):
    page = ForgotPasswordPage(unauthenticated_driver, base_url)
    page.open()
    assert page.find(*page.EMAIL).get_attribute("type") == "email"


def test_reset_password_empty_submit_blocked(unauthenticated_driver, base_url):
    page = ResetPasswordPage(unauthenticated_driver, base_url)
    page.open(token="any-nonempty-token-value")
    page.submit()
    assert page.shows_form(), "empty submit must not navigate away from the reset form"
