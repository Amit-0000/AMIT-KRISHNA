"""Mobile-web coverage of VoiceGuard's fully public, unguarded pages
(landing page, unknown-route 404) — mirrors e2e/selenium/test_public_pages.py's
landing/404 checks through Appium's mobile Chrome instead of desktop headless
Chrome."""
from __future__ import annotations

from pages.auth_pages import LandingPage, NotFoundPage


def test_landing_page_loads_on_mobile_chrome(driver, base_url):
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
