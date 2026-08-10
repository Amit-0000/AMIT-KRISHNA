"""Mobile-web coverage of /dashboard (Dashboard/index.tsx).

DashboardHeader (greeting + "Analyze Audio") renders unconditionally; the
rest of the page is either EmptyDashboard or the full stats/QuickActions
grid depending on whether the shared fixture account has any scans yet --
both are real, reachable states, so tests assert on whichever is present
rather than assuming one.
"""
from __future__ import annotations

import pytest

from data.users import FIXTURE_USER
from pages.dashboard_page import DashboardPage


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
    dashboard.tap_analyze_audio()
    dashboard.wait_url_contains("/scan/new")
    assert "/scan/new" in dashboard.current_url


def test_dashboard_view_history_quick_action_navigates_when_populated(authenticated_driver, base_url):
    dashboard = DashboardPage(authenticated_driver, base_url)
    dashboard.goto_dashboard()
    if not dashboard.is_populated_state():
        pytest.skip("fixture account currently has zero scans -- QuickActions doesn't render (EmptyDashboard does instead)")
    dashboard.tap_view_history_quick_action()
    dashboard.wait_url_contains("/history")
    assert "/history" in dashboard.current_url


def test_dashboard_no_horizontal_overflow_on_mobile_viewport(authenticated_driver, base_url):
    dashboard = DashboardPage(authenticated_driver, base_url)
    dashboard.goto_dashboard()
    overflow = authenticated_driver.execute_script(
        "return document.documentElement.scrollWidth - document.documentElement.clientWidth;"
    )
    assert overflow <= 1, f"page scrolls horizontally by {overflow}px on the mobile viewport"
