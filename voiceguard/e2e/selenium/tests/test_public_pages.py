"""Desktop coverage of VoiceGuard's fully public, unguarded pages (landing
page, unknown-route 404). Absorbs the old top-level test_public_pages.py's
test_landing_page_loads and test_unknown_route_shows_404 (same assertions,
now through the Page Object Model)."""
from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By

from pages.auth_pages import LandingPage, NotFoundPage

pytestmark = [pytest.mark.medium]


def test_landing_page_loads(driver, base_url):
    page = LandingPage(driver, base_url)
    page.open()
    assert driver.title
    assert page.current_url.rstrip("/") == base_url.rstrip("/")


def test_landing_page_main_content_visible(driver, base_url):
    page = LandingPage(driver, base_url)
    page.open()
    assert page.main_content_visible()


def test_unknown_route_shows_404(driver, base_url):
    page = NotFoundPage(driver, base_url)
    page.open_unknown_route()
    assert page.shows_404()


def test_404_page_has_return_home_link(driver, base_url):
    page = NotFoundPage(driver, base_url)
    page.open_unknown_route()
    assert page.is_visible(*page.RETURN_HOME_LINK)


def test_404_page_return_home_link_navigates_to_landing_page(driver, base_url):
    page = NotFoundPage(driver, base_url)
    page.open_unknown_route()
    page.click(page.find_clickable(*page.RETURN_HOME_LINK))
    assert page.current_url.rstrip("/") == base_url.rstrip("/")


def test_404_page_shown_for_a_nested_unknown_route(driver, base_url):
    page = NotFoundPage(driver, base_url)
    page.goto("/this/nested/route/does-not-exist")
    assert page.shows_404()


def test_landing_page_analyze_audio_cta_navigates_to_signup(unauthenticated_driver, base_url):
    # unauthenticated_driver, not plain driver: the target is /signup, a
    # GuestGuard route -- reusing this suite's shared session-scoped driver
    # while it happens to already be authenticated (near-certain by the
    # time this file runs, alphabetically well after test_auth.py and
    # friends) would have GuestGuard bounce this navigation straight to
    # /dashboard instead of /signup, same as every other GuestGuard-route
    # test in this suite (see README's "Fixture design" section).
    #
    # js_click, not click(): same confirmed-live React Router <Link> click
    # quirk documented on BasePage.js_click (native WebDriver click doesn't
    # reliably trigger client-side navigation on these elements in headless
    # Chrome).
    page = LandingPage(unauthenticated_driver, base_url)
    page.open()
    cta = page.find_clickable(By.XPATH, "(//a[@href='/signup'])[1]")
    page.js_click(cta)
    page.wait_url_contains("/signup")
    assert "/signup" in page.current_url


def test_landing_page_sign_in_link_navigates_to_login(unauthenticated_driver, base_url):
    # unauthenticated_driver -- see test_landing_page_analyze_audio_cta_
    # navigates_to_signup's comment; /login is a GuestGuard route too.
    page = LandingPage(unauthenticated_driver, base_url)
    page.open()
    link = page.find_clickable(By.XPATH, "(//a[@href='/login'])[1]")
    page.js_click(link)
    page.wait_url_contains("/login")
    assert "/login" in page.current_url


def test_landing_page_has_skip_to_content_link(driver, base_url):
    page = LandingPage(driver, base_url)
    page.open()
    assert page.is_present(By.CSS_SELECTOR, 'a[href="#main-content"]')


def test_landing_page_has_a_document_title(driver, base_url):
    page = LandingPage(driver, base_url)
    page.open()
    assert len(driver.title) > 0


def test_landing_page_reachable_via_trailing_slash(driver, base_url):
    page = LandingPage(driver, base_url)
    page.goto("/")
    assert page.main_content_visible()


def test_404_page_body_does_not_leak_stack_trace(driver, base_url):
    # A real, minimal information-disclosure guard: an unknown route must
    # render the app's own 404 copy, never a raw framework/server error
    # page with file paths or stack frames in it.
    page = NotFoundPage(driver, base_url)
    page.open_unknown_route()
    body = page.body_text().lower()
    assert "traceback" not in body
    assert "at react" not in body


def test_unknown_route_with_hash_fragment_shows_404(driver, base_url):
    page = NotFoundPage(driver, base_url)
    page.goto("/this-route-does-not-exist#section")
    assert page.shows_404()
