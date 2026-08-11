"""Desktop registration coverage (/signup, GuestGuard-protected).

Only "successful signup" and "duplicate email" actually call the backend —
every other case here is blocked by react-hook-form + zod client-side
validation (frontend/src/pages/Signup/index.tsx's onSubmit never fires),
matching the real validation rules in frontend/src/lib/validation.ts.

Absorbs the old top-level test_public_pages.py's
test_signup_page_renders_required_fields,
test_signup_client_side_validation_blocks_empty_submit, and
test_signup_rejects_mismatched_passwords.
"""
from __future__ import annotations

import pytest

from data.test_inputs import INVALID_DISPLAY_NAMES, INVALID_EMAILS, MISMATCHED_PASSWORD, WEAK_PASSWORDS
from data.users import FIXTURE_USER, VALID_SIGNUP_PASSWORD, unique_signup_email
from pages.auth_pages import SignupPage

pytestmark = [pytest.mark.high]


def test_signup_page_renders_required_fields(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    assert page.is_visible(*page.DISPLAY_NAME)
    assert page.is_visible(*page.EMAIL)
    assert page.is_visible(*page.PASSWORD)
    assert page.is_visible(*page.CONFIRM_PASSWORD)


def test_signup_form_accepts_input(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.fill_id("displayName", "Selenium QA")
    assert page.find(*page.DISPLAY_NAME).get_attribute("value") == "Selenium QA"


def test_signup_empty_submit_blocked(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.submit_signup()
    assert "/signup" in page.current_url, "empty submit must not navigate away from the form"


def test_signup_rejects_mismatched_passwords(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.fill_form("Selenium QA", "selenium.mismatch@example.com", VALID_SIGNUP_PASSWORD, MISMATCHED_PASSWORD)
    page.submit_signup()
    assert "match" in page.body_text().lower()


@pytest.mark.parametrize("rule", sorted(WEAK_PASSWORDS))
def test_signup_rejects_weak_password(unauthenticated_driver, base_url, rule):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    weak = WEAK_PASSWORDS[rule]
    page.fill_form("Selenium QA", "selenium.weakpw@example.com", weak, weak)
    page.submit_signup()
    assert "/signup" in page.current_url, f"weak password ({rule}) must not be accepted"


@pytest.mark.parametrize("invalid_email", INVALID_EMAILS)
def test_signup_rejects_invalid_email(unauthenticated_driver, base_url, invalid_email):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.fill_form("Selenium QA", invalid_email, VALID_SIGNUP_PASSWORD, VALID_SIGNUP_PASSWORD)
    page.submit_signup()
    assert "/signup" in page.current_url, f"invalid email {invalid_email!r} must not be accepted"


@pytest.mark.parametrize("rule", sorted(INVALID_DISPLAY_NAMES))
def test_signup_rejects_invalid_display_names(unauthenticated_driver, base_url, rule):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.fill_form(
        INVALID_DISPLAY_NAMES[rule], "selenium.badname@example.com", VALID_SIGNUP_PASSWORD, VALID_SIGNUP_PASSWORD
    )
    page.submit_signup()
    assert "/signup" in page.current_url, f"invalid display name ({rule}) must not be accepted"


def test_signup_duplicate_email_rejected(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.fill_form("Selenium QA Dup", FIXTURE_USER["email"], VALID_SIGNUP_PASSWORD, VALID_SIGNUP_PASSWORD)
    page.submit_signup()
    assert "already exists" in page.body_text().lower()


def test_signup_success_shows_check_email(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.fill_form("Selenium QA New", unique_signup_email(), VALID_SIGNUP_PASSWORD, VALID_SIGNUP_PASSWORD)
    page.submit_signup()
    assert page.check_email_message_shown()


def test_signup_password_field_uses_password_input_type(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    assert page.find(*page.PASSWORD).get_attribute("type") == "password"


def test_signup_confirm_password_field_uses_password_input_type(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    assert page.find(*page.CONFIRM_PASSWORD).get_attribute("type") == "password"


def test_signup_email_field_uses_email_input_type(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    assert page.find(*page.EMAIL).get_attribute("type") == "email"


def test_signup_whitespace_only_display_name_rejected(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.fill_form("   ", "selenium.wsname@example.com", VALID_SIGNUP_PASSWORD, VALID_SIGNUP_PASSWORD)
    page.submit_signup()
    assert "/signup" in page.current_url, "a whitespace-only display name must not be accepted"


def test_signup_form_retains_entered_email_after_client_side_rejection(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    email = "selenium.retained@example.com"
    page.fill_form("Selenium QA", email, VALID_SIGNUP_PASSWORD, MISMATCHED_PASSWORD)
    page.submit_signup()
    assert page.find(*page.EMAIL).get_attribute("value") == email


def test_signup_login_link_navigates_to_login(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    link = page.find_clickable("xpath", "//a[@href='/login']")
    page.js_click(link)
    page.wait_url_contains("/login")
    assert "/login" in page.current_url
