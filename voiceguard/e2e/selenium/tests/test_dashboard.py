"""Desktop coverage of /dashboard (Dashboard/index.tsx).

DashboardHeader (greeting + "Analyze Audio") renders unconditionally; the
rest of the page is either EmptyDashboard or the full stats/QuickActions
grid depending on whether the shared fixture account has any scans yet --
both are real, reachable states, so tests assert on whichever is present
rather than assuming one. Same component as the Appium suite covers.
"""
from __future__ import annotations

import pytest

from data.users import FIXTURE_USER
from pages.dashboard_page import DashboardPage

pytestmark = [pytest.mark.high]


def test_dashboard_renders_greeting_header(authenticated_driver, base_url):
    dashboard = DashboardPage(authenticated_driver, base_url)
    dashboard.goto_dashboard()
    greeting = dashboard.greeting_text()
    assert greeting.startswith(("Good morning", "Good afternoon", "Good evening"))


def test_dashboard_greeting_includes_first_name(authenticated_driver, base_url):
    dashboard = DashboardPage(authenticated_driver, base_url)
    dashboard.goto_dashboard()
    first_name = FIXTURE_USER["display_name"].split(" ")[0]
    assert first_name in dashboard.greeting_text()


def test_dashboard_shows_a_reachable_state(authenticated_driver, base_url):
    dashboard = DashboardPage(authenticated_driver, base_url)
    dashboard.goto_dashboard()
    assert dashboard.is_empty_state() or dashboard.is_populated_state()


def test_dashboard_analyze_audio_header_link_navigates_to_new_scan(authenticated_driver, base_url):
    dashboard = DashboardPage(authenticated_driver, base_url)
    dashboard.goto_dashboard()
    dashboard.click_analyze_audio()
    dashboard.wait_url_contains("/scan/new")
    assert "/scan/new" in dashboard.current_url


def test_dashboard_view_history_quick_action_navigates_when_populated(authenticated_driver, base_url):
    dashboard = DashboardPage(authenticated_driver, base_url)
    dashboard.goto_dashboard()
    if not dashboard.is_populated_state():
        pytest.skip("fixture account currently has zero scans -- QuickActions doesn't render (EmptyDashboard does instead)")
    dashboard.click_view_history_quick_action()
    dashboard.wait_url_contains("/history")
    assert "/history" in dashboard.current_url


def test_dashboard_page_title_is_set(authenticated_driver, base_url):
    dashboard = DashboardPage(authenticated_driver, base_url)
    dashboard.goto_dashboard()
    assert authenticated_driver.title


def test_dashboard_greeting_is_an_h1_heading(authenticated_driver, base_url):
    dashboard = DashboardPage(authenticated_driver, base_url)
    dashboard.goto_dashboard()
    assert dashboard.find(*dashboard.GREETING_HEADING).tag_name == "h1"


def test_dashboard_reachable_directly_via_url_when_authenticated(authenticated_driver, base_url):
    # Regression check for a real class of bug: a client-side-only route
    # guard that only works after an in-app navigation, not a hard reload/
    # direct URL hit — goto_dashboard() below performs a real driver.get().
    dashboard = DashboardPage(authenticated_driver, base_url)
    dashboard.goto_dashboard()
    assert "/dashboard" in dashboard.current_url
    assert "/login" not in dashboard.current_url


def test_dashboard_analyze_audio_link_has_href_to_scan_new(authenticated_driver, base_url):
    dashboard = DashboardPage(authenticated_driver, base_url)
    dashboard.goto_dashboard()
    link = dashboard.find_clickable(*dashboard.ANALYZE_AUDIO_HEADER_LINK)
    assert link.get_attribute("href").endswith("/scan/new")


def test_dashboard_title_bar_reflects_app_name(authenticated_driver, base_url):
    dashboard = DashboardPage(authenticated_driver, base_url)
    dashboard.goto_dashboard()
    assert "VoiceGuard" in authenticated_driver.title


def test_dashboard_empty_and_populated_states_are_mutually_exclusive(authenticated_driver, base_url):
    dashboard = DashboardPage(authenticated_driver, base_url)
    dashboard.goto_dashboard()
    # EmptyDashboard and the QuickActions grid are alternate renders of the
    # same slot (DashboardPage's own docstring) — they must never both be
    # on the page at once.
    assert not (dashboard.is_empty_state() and dashboard.is_populated_state())
