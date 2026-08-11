"""Desktop coverage of the 3-step /onboarding flow (AuthGuard-protected,
frontend/src/pages/Onboarding/index.tsx). Visiting /onboarding directly has
no completion gate of its own (only OnboardingGuard, which wraps the
authenticated app shell rather than this route, cares about
onboarding_completed) — so this flow is reachable and testable even with an
already-onboarded fixture account."""
from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By

from pages.onboarding_page import CURIOSITY_OPTION_XPATH, OnboardingPage

pytestmark = [pytest.mark.medium]


def test_onboarding_welcome_step_shown(authenticated_driver, base_url):
    page = OnboardingPage(authenticated_driver, base_url)
    page.open()
    assert page.welcome_step_shown()


def test_onboarding_advances_to_use_case_step(authenticated_driver, base_url):
    page = OnboardingPage(authenticated_driver, base_url)
    page.open()
    page.click_get_started()
    assert page.use_case_step_shown()


def test_onboarding_advances_to_privacy_step(authenticated_driver, base_url):
    page = OnboardingPage(authenticated_driver, base_url)
    page.open()
    page.click_get_started()
    page.select_curiosity_use_case()
    page.click_continue()
    assert page.privacy_step_shown()


def test_onboarding_finish_navigates_to_dashboard(authenticated_driver, base_url):
    page = OnboardingPage(authenticated_driver, base_url)
    page.open()
    page.click_get_started()
    page.select_curiosity_use_case()
    page.click_continue()
    page.finish()
    page.wait_url_contains("/dashboard")
    assert "/dashboard" in authenticated_driver.current_url


def test_onboarding_reachable_directly_via_url_when_authenticated(authenticated_driver, base_url):
    page = OnboardingPage(authenticated_driver, base_url)
    page.open()
    assert "/onboarding" in page.current_url
    assert "/login" not in page.current_url


def test_onboarding_use_case_step_shows_curiosity_option(authenticated_driver, base_url):
    page = OnboardingPage(authenticated_driver, base_url)
    page.open()
    page.click_get_started()
    assert page.is_visible(By.XPATH, CURIOSITY_OPTION_XPATH)


def test_onboarding_privacy_step_shows_a_real_list(authenticated_driver, base_url):
    page = OnboardingPage(authenticated_driver, base_url)
    page.open()
    page.click_get_started()
    page.select_curiosity_use_case()
    page.click_continue()
    items = page.find_all(By.CSS_SELECTOR, "ul[role=list] li")
    assert len(items) > 0, "privacy step should list at least one real privacy point"
