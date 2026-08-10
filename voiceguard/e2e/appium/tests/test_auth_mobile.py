"""Mobile-web login + email-verification coverage (/login, /verify-email)."""
from __future__ import annotations

from data.test_inputs import WRONG_LOGIN_CREDENTIALS
from data.users import FIXTURE_USER
from pages.auth_pages import LoginPage, VerifyEmailPage
from pages.base_page import BasePage


def test_login_page_renders_on_mobile_viewport(unauthenticated_driver, base_url):
    page = LoginPage(unauthenticated_driver, base_url)
    page.open()
    assert page.is_visible(*page.EMAIL)
    assert page.is_visible(*page.PASSWORD)


def test_login_empty_submit_blocked(unauthenticated_driver, base_url):
    page = LoginPage(unauthenticated_driver, base_url)
    page.open()
    page.submit()
    assert "/login" in page.current_url, "empty submit must not navigate away from the form"


def test_login_rejects_bad_credentials(unauthenticated_driver, base_url):
    page = LoginPage(unauthenticated_driver, base_url)
    page.open()
    page.login(WRONG_LOGIN_CREDENTIALS["email"], WRONG_LOGIN_CREDENTIALS["password"])
    msg = page.error_message().lower()
    assert "incorrect" in msg or "credentials" in msg


def test_forgot_password_link_navigates_from_login(unauthenticated_driver, base_url):
    page = LoginPage(unauthenticated_driver, base_url)
    page.open()
    page.tap(page.find_clickable(*page.FORGOT_PASSWORD_LINK))
    page.wait_url_contains("/forgot-password")


def test_login_with_valid_credentials_reaches_dashboard(authenticated_driver, base_url):
    # authenticated_driver already performed this login (once, session-wide)
    # and waited for /dashboard — this test is an explicit regression check
    # on that guarantee, not a re-login.
    assert "/dashboard" in authenticated_driver.current_url


def test_login_session_persists_after_reload(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.goto("/dashboard")
    authenticated_driver.refresh()
    page.wait_url_contains("/dashboard")
    assert "/dashboard" in authenticated_driver.current_url, "a hard reload must not drop the session"


def test_verify_email_missing_token_shows_message(driver, base_url):
    page = VerifyEmailPage(driver, base_url)
    page.open()
    assert page.shows_missing_token_message()


def test_verify_email_invalid_token_shows_error(driver, base_url):
    page = VerifyEmailPage(driver, base_url)
    page.open(token="0" * 64)
    assert page.shows_invalid_or_expired_message()


def test_verify_email_resend_shows_confirmation(driver, base_url):
    page = VerifyEmailPage(driver, base_url)
    page.open()  # missing-token state also renders the resend form
    page.resend_to(FIXTURE_USER["email"])
    assert page.resend_confirmation_shown()
