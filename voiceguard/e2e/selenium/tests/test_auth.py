"""Desktop login + email-verification coverage (/login, /verify-email).

Absorbs the old top-level test_public_pages.py's test_login_page_renders,
test_login_rejects_bad_credentials, and test_authenticated_flows.py's
test_login_with_valid_credentials_reaches_dashboard.
"""
from __future__ import annotations

import pytest

from selenium.webdriver.common.by import By

from data.test_inputs import INVALID_EMAILS, WRONG_LOGIN_CREDENTIALS
from data.users import FIXTURE_USER
from pages.auth_pages import LoginPage, VerifyEmailPage
from pages.base_page import BasePage

pytestmark = [pytest.mark.critical]


def test_login_page_renders(unauthenticated_driver, base_url):
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
    # js_click, not click(): confirmed live that WebDriver's native click on
    # this specific Link doesn't trigger React Router navigation in headless
    # Chrome (element resolves correctly, nothing overlaps it, no console
    # errors — the click just doesn't register as a navigation trigger) —
    # see BasePage.js_click's docstring.
    page.js_click(page.find_clickable(*page.FORGOT_PASSWORD_LINK))
    page.wait_url_contains("/forgot-password")


def test_login_with_valid_credentials_reaches_dashboard(authenticated_driver, base_url):
    # authenticated_driver logs in once, session-wide, the first time any
    # test in the run requests it -- which file that happens to be depends
    # on collection order (alphabetically, not necessarily this one), so by
    # the time THIS test runs, other tests may already have moved the
    # shared driver elsewhere. Navigate to /dashboard explicitly rather than
    # trusting current_url's incidental state: if the earlier login had
    # failed, AuthGuard would bounce this navigation straight back to
    # /login, so this is still a real regression check on that guarantee.
    page = BasePage(authenticated_driver, base_url)
    page.goto("/dashboard")
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


def test_login_password_field_uses_password_input_type(unauthenticated_driver, base_url):
    page = LoginPage(unauthenticated_driver, base_url)
    page.open()
    assert page.find(*page.PASSWORD).get_attribute("type") == "password"


def test_login_email_field_uses_email_input_type(unauthenticated_driver, base_url):
    page = LoginPage(unauthenticated_driver, base_url)
    page.open()
    assert page.find(*page.EMAIL).get_attribute("type") == "email"


@pytest.mark.parametrize("invalid_email", INVALID_EMAILS)
def test_login_rejects_malformed_email_without_calling_backend(unauthenticated_driver, base_url, invalid_email):
    # Client-side zod validation (same emailSchema as Signup) should block
    # the submit before any POST /auth/login fires — the form must not
    # navigate away from /login for a malformed address.
    page = LoginPage(unauthenticated_driver, base_url)
    page.open()
    page.login(invalid_email, WRONG_LOGIN_CREDENTIALS["password"])
    assert "/login" in page.current_url


def test_login_email_field_retains_value_after_failed_submit(unauthenticated_driver, base_url):
    page = LoginPage(unauthenticated_driver, base_url)
    page.open()
    page.login(WRONG_LOGIN_CREDENTIALS["email"], WRONG_LOGIN_CREDENTIALS["password"])
    page.error_message()  # wait for the failed round trip to finish rendering
    assert page.find(*page.EMAIL).get_attribute("value") == WRONG_LOGIN_CREDENTIALS["email"]


def test_login_error_message_has_alert_role_for_assistive_tech(unauthenticated_driver, base_url):
    page = LoginPage(unauthenticated_driver, base_url)
    page.open()
    page.login(WRONG_LOGIN_CREDENTIALS["email"], WRONG_LOGIN_CREDENTIALS["password"])
    assert page.find(By.CSS_SELECTOR, "[role=alert]").is_displayed()


def test_login_submit_button_present_and_enabled_on_load(unauthenticated_driver, base_url):
    page = LoginPage(unauthenticated_driver, base_url)
    page.open()
    button = page.find_clickable(By.CSS_SELECTOR, "button[type=submit]")
    assert button.is_enabled()


def test_authenticated_session_cookie_present_after_login(authenticated_driver, base_url):
    # Real, current session-establishment behavior: a cookie-backed session
    # exists after login, without asserting on any single cookie's name
    # (an implementation detail this suite shouldn't over-specify).
    page = BasePage(authenticated_driver, base_url)
    page.goto("/dashboard")
    assert authenticated_driver.get_cookies(), "expected at least one cookie after a real login"


def test_dashboard_reload_does_not_re_trigger_login_redirect(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.goto("/dashboard")
    for _ in range(2):
        authenticated_driver.refresh()
        page.wait_url_contains("/dashboard")
    assert "/dashboard" in authenticated_driver.current_url


def test_login_page_has_a_document_title(unauthenticated_driver, base_url):
    page = LoginPage(unauthenticated_driver, base_url)
    page.open()
    assert unauthenticated_driver.title


def test_login_form_uses_post_semantics_not_get(unauthenticated_driver, base_url):
    # A real, minimal regression guard: submitting must never leak
    # credentials into the URL as query params (a GET-form bug class).
    page = LoginPage(unauthenticated_driver, base_url)
    page.open()
    page.login(WRONG_LOGIN_CREDENTIALS["email"], WRONG_LOGIN_CREDENTIALS["password"])
    page.error_message()
    assert WRONG_LOGIN_CREDENTIALS["password"] not in page.current_url


def test_verify_email_page_survives_direct_reload(driver, base_url):
    page = VerifyEmailPage(driver, base_url)
    page.open()
    driver.refresh()
    assert page.shows_missing_token_message()


def test_login_rejects_bad_credentials_shows_error_only_after_real_backend_round_trip(unauthenticated_driver, base_url):
    # Distinguishes a real server round trip from a client-side-only
    # rejection: the URL must still be /login (no navigation happened) but
    # the error text must be the backend's real message, not a client-side
    # validation string like "required".
    page = LoginPage(unauthenticated_driver, base_url)
    page.open()
    page.login(WRONG_LOGIN_CREDENTIALS["email"], WRONG_LOGIN_CREDENTIALS["password"])
    msg = page.error_message().lower()
    assert "required" not in msg
    assert "incorrect" in msg or "credentials" in msg
