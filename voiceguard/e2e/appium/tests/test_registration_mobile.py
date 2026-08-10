"""Mobile-web registration coverage (/signup, GuestGuard-protected).

Only "successful signup" and "duplicate email" actually call the backend —
every other case here is blocked by react-hook-form + zod client-side
validation (frontend/src/pages/Signup/index.tsx's onSubmit never fires),
matching the real validation rules in frontend/src/lib/validation.ts.
"""
from __future__ import annotations

import pytest

from data.test_inputs import INVALID_DISPLAY_NAMES, INVALID_EMAILS, MISMATCHED_PASSWORD, WEAK_PASSWORDS
from data.users import FIXTURE_USER, VALID_SIGNUP_PASSWORD, unique_signup_email
from pages.auth_pages import SignupPage


def test_signup_page_renders_required_fields(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    assert page.is_visible(*page.DISPLAY_NAME)
    assert page.is_visible(*page.EMAIL)
    assert page.is_visible(*page.PASSWORD)
    assert page.is_visible(*page.CONFIRM_PASSWORD)


def test_signup_form_is_usable_via_touch(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.fill_id("displayName", "Appium QA")
    assert page.find(*page.DISPLAY_NAME).get_attribute("value") == "Appium QA"


def test_signup_empty_submit_blocked(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.submit_signup()
    assert "/signup" in page.current_url, "empty submit must not navigate away from the form"


def test_signup_rejects_mismatched_passwords(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.fill_form("Appium QA", "appium.mismatch@example.com", VALID_SIGNUP_PASSWORD, MISMATCHED_PASSWORD)
    page.submit_signup()
    assert "match" in page.body_text().lower()


@pytest.mark.parametrize("rule", sorted(WEAK_PASSWORDS))
def test_signup_rejects_weak_password(unauthenticated_driver, base_url, rule):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    weak = WEAK_PASSWORDS[rule]
    page.fill_form("Appium QA", "appium.weakpw@example.com", weak, weak)
    page.submit_signup()
    assert "/signup" in page.current_url, f"weak password ({rule}) must not be accepted"


@pytest.mark.parametrize("invalid_email", INVALID_EMAILS)
def test_signup_rejects_invalid_email(unauthenticated_driver, base_url, invalid_email):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.fill_form("Appium QA", invalid_email, VALID_SIGNUP_PASSWORD, VALID_SIGNUP_PASSWORD)
    page.submit_signup()
    assert "/signup" in page.current_url, f"invalid email {invalid_email!r} must not be accepted"


def test_signup_rejects_invalid_display_names(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    for name in INVALID_DISPLAY_NAMES.values():
        page.open()
        page.fill_form(name, "appium.badname@example.com", VALID_SIGNUP_PASSWORD, VALID_SIGNUP_PASSWORD)
        page.submit_signup()
        assert "/signup" in page.current_url


def test_signup_duplicate_email_rejected(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.fill_form("Appium QA Dup", FIXTURE_USER["email"], VALID_SIGNUP_PASSWORD, VALID_SIGNUP_PASSWORD)
    page.submit_signup()
    assert "already exists" in page.body_text().lower()


def test_signup_success_shows_check_email(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    page.fill_form("Appium QA New", unique_signup_email(), VALID_SIGNUP_PASSWORD, VALID_SIGNUP_PASSWORD)
    page.submit_signup()
    assert page.check_email_message_shown()
