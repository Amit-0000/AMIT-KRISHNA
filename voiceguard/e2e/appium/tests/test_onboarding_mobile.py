"""Mobile-web coverage of the 3-step /onboarding flow (AuthGuard-protected,
frontend/src/pages/Onboarding/index.tsx). Visiting /onboarding directly has
no completion gate of its own (only OnboardingGuard, which wraps the
authenticated app shell rather than this route, cares about
onboarding_completed) — so this flow is reachable and testable even with an
already-onboarded fixture account."""
from __future__ import annotations

from pages.onboarding_page import OnboardingPage


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
