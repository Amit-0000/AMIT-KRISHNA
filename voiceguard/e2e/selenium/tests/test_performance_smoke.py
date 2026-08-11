"""Desktop-only performance-smoke coverage — genuinely new relative to the
Appium suite (mobile emulator timing is dominated by emulator/instrumentation
overhead documented elsewhere as unreliable; a real Chrome process on the CI
runner gives a cleaner signal).

Uses the real Navigation Timing Level 2 API (`performance.getEntriesByType
('navigation')[0]`), not a hand-rolled timer, and asserts generous,
explicitly-reasoned thresholds rather than a number copied from a production
SLA that doesn't apply to a Vite dev-server-backed page running in CI docker
compose (no CDN, no build-time minification/tree-shaking of the kind a real
prod deploy would have) — same calibrate-to-the-real-environment honesty bar
as performance/k6/baseline_load_test.js's p(95)<1500ms threshold comment.
"""
from __future__ import annotations

import pytest

from pages.base_page import BasePage

pytestmark = [pytest.mark.low]

# Generous on purpose: Vite's dev server (no production build/minification/
# code-splitting-at-the-CDN-edge) plus a Docker-Compose-networked backend
# inside the same CI runner as everything else in this job. This is a smoke
# ceiling to catch a real regression (e.g. an accidental blocking call, a
# runaway bundle), not a production SLA.
DOM_CONTENT_LOADED_CEILING_MS = 8000
LOAD_EVENT_CEILING_MS = 12000


def _navigation_timing(driver) -> dict:
    return driver.execute_script(
        "const e = performance.getEntriesByType('navigation')[0]; "
        "return e ? {"
        "  domContentLoaded: e.domContentLoadedEventEnd - e.startTime, "
        "  loadEvent: e.loadEventEnd - e.startTime, "
        "  responseStart: e.responseStart - e.startTime"
        "} : null;"
    )


def test_landing_page_navigation_timing_api_is_available(driver, base_url):
    page = BasePage(driver, base_url)
    page.goto("/")
    timing = _navigation_timing(page.driver)
    assert timing is not None, "browser should expose a real navigation timing entry"


def test_landing_page_dom_content_loaded_within_ceiling(driver, base_url):
    page = BasePage(driver, base_url)
    page.goto("/")
    timing = _navigation_timing(page.driver)
    assert timing["domContentLoaded"] < DOM_CONTENT_LOADED_CEILING_MS, timing


def test_landing_page_full_load_within_ceiling(driver, base_url):
    page = BasePage(driver, base_url)
    page.goto("/")
    timing = _navigation_timing(page.driver)
    assert timing["loadEvent"] < LOAD_EVENT_CEILING_MS, timing


def test_login_page_dom_content_loaded_within_ceiling(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/login")
    timing = _navigation_timing(page.driver)
    assert timing["domContentLoaded"] < DOM_CONTENT_LOADED_CEILING_MS, timing


def test_dashboard_dom_content_loaded_within_ceiling(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.goto("/dashboard")
    timing = _navigation_timing(page.driver)
    assert timing["domContentLoaded"] < DOM_CONTENT_LOADED_CEILING_MS, timing


def test_backend_first_byte_within_ceiling_on_dashboard(authenticated_driver, base_url):
    # responseStart isolates real backend/network latency from client-side
    # render time — a much tighter, more meaningful ceiling than the full
    # page-load numbers above.
    page = BasePage(authenticated_driver, base_url)
    page.goto("/dashboard")
    timing = _navigation_timing(page.driver)
    assert timing["responseStart"] < 3000, timing


AUTHENTICATED_ROUTES_FOR_TIMING = ["/history", "/notifications", "/help", "/feedback", "/scan/new", "/settings/profile"]


@pytest.mark.parametrize("route", AUTHENTICATED_ROUTES_FOR_TIMING)
def test_authenticated_route_dom_content_loaded_within_ceiling(authenticated_driver, base_url, route):
    page = BasePage(authenticated_driver, base_url)
    page.goto(route)
    timing = _navigation_timing(page.driver)
    assert timing["domContentLoaded"] < DOM_CONTENT_LOADED_CEILING_MS, (route, timing)


def test_signup_page_dom_content_loaded_within_ceiling(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/signup")
    timing = _navigation_timing(page.driver)
    assert timing["domContentLoaded"] < DOM_CONTENT_LOADED_CEILING_MS, timing


def test_history_backend_first_byte_within_ceiling(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.goto("/history")
    timing = _navigation_timing(page.driver)
    assert timing["responseStart"] < 3000, timing


def test_landing_page_response_start_within_ceiling(driver, base_url):
    page = BasePage(driver, base_url)
    page.goto("/")
    timing = _navigation_timing(page.driver)
    assert timing["responseStart"] < 3000, timing
