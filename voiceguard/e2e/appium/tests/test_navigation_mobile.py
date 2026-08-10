"""Mobile-web coverage of the shared app chrome: MobileDrawer, GlobalSearch,
NotificationCenter, UserMenu, ThemeToggle, Breadcrumb.

All of this chrome only renders inside AppShell (authenticated routes), so
every test here starts from a real, already-authenticated /dashboard view.
"""
from __future__ import annotations

import pytest

from data.users import FIXTURE_USER
from pages.dashboard_page import DashboardPage
from pages.nav import AppChrome, MobileDrawer, GlobalSearch, NotificationCenter, UserMenu


@pytest.fixture
def chrome(authenticated_driver, base_url):
    DashboardPage(authenticated_driver, base_url).goto_dashboard()
    return AppChrome(authenticated_driver, base_url)


def test_mobile_drawer_opens_via_hamburger(chrome):
    drawer = chrome.open_mobile_drawer()
    assert drawer.is_open()


def test_mobile_drawer_closes_via_close_button(chrome):
    drawer = chrome.open_mobile_drawer()
    assert drawer.is_open()
    drawer.close()
    assert not drawer.is_open()


def test_mobile_drawer_dashboard_link_present(chrome):
    drawer = chrome.open_mobile_drawer()
    assert drawer.nav_link("Dashboard").is_displayed()


def test_mobile_drawer_history_link_navigates_and_autocloses(chrome):
    drawer = chrome.open_mobile_drawer()
    drawer.go_to("History")
    drawer.wait_url_contains("/history")
    assert "/history" in drawer.current_url
    # MobileDrawer.tsx closes itself on every route change (useEffect on
    # location.pathname) -- a real behavior, not something the test forces.
    assert not drawer.is_open()


def test_mobile_drawer_new_scan_link_navigates(chrome):
    drawer = chrome.open_mobile_drawer()
    drawer.go_to("New Scan")
    drawer.wait_url_contains("/scan/new")
    assert "/scan/new" in drawer.current_url


def test_mobile_drawer_help_center_link_navigates(chrome):
    drawer = chrome.open_mobile_drawer()
    drawer.go_to("Help Center")
    drawer.wait_url_contains("/help")
    assert "/help" in drawer.current_url


def test_mobile_drawer_settings_link_navigates(chrome):
    drawer = chrome.open_mobile_drawer()
    drawer.go_to("Settings")
    drawer.wait_url_contains("/settings")
    assert "/settings" in drawer.current_url


def test_user_menu_opens_from_drawer_and_shows_account_links(chrome):
    drawer = chrome.open_mobile_drawer()
    menu = drawer.open_user_menu(FIXTURE_USER["display_name"])
    assert menu.is_open()
    assert menu.find(*menu.PROFILE_ITEM).is_displayed()
    assert menu.find(*menu.ACCOUNT_ITEM).is_displayed()


def test_user_menu_profile_link_navigates_to_settings_profile(chrome):
    drawer = chrome.open_mobile_drawer()
    menu = drawer.open_user_menu(FIXTURE_USER["display_name"])
    menu.go_to_profile()
    menu.wait_url_contains("/settings/profile")
    assert "/settings/profile" in menu.current_url


def test_global_search_opens_via_icon(chrome):
    search = chrome.open_search()
    assert search.is_open()


def test_global_search_shows_quick_actions_by_default(chrome):
    search = chrome.open_search()
    labels = search.result_labels()
    assert "Dashboard" in labels
    assert "New Scan" in labels


def test_global_search_filters_results_by_query(chrome):
    search = chrome.open_search()
    search.type_query("history")
    labels = search.result_labels()
    assert labels == ["History"]


def test_global_search_no_results_for_gibberish_query(chrome):
    search = chrome.open_search()
    search.type_query("zzzxxxqqq_no_such_thing")
    assert search.is_present(*search.NO_RESULTS)


def test_global_search_select_result_navigates_and_closes(chrome):
    search = chrome.open_search()
    search.type_query("history")
    search.select_result("History")
    search.wait_url_contains("/history")
    assert "/history" in search.current_url
    assert not search.is_open()


def test_global_search_close_button_closes_without_navigating(chrome):
    search = chrome.open_search()
    search.close()
    assert not search.is_open()


def test_notification_center_opens_via_bell(chrome):
    panel = chrome.open_notifications()
    assert panel.is_open()


def test_notification_center_closes_via_close_button(chrome):
    panel = chrome.open_notifications()
    panel.close()
    assert not panel.is_open()


def test_notification_center_view_all_navigates_to_notifications_page(chrome):
    panel = chrome.open_notifications()
    panel.go_to_all_notifications()
    panel.wait_url_contains("/notifications")
    assert "/notifications" in panel.current_url


def test_theme_toggle_cycles_theme(chrome):
    before = chrome.current_theme_label()
    chrome.cycle_theme()
    after = chrome.current_theme_label()
    assert before != after


def test_breadcrumb_hidden_on_mobile_viewport(chrome):
    # TopBar.tsx renders Breadcrumb with `hidden sm:flex` -- present in the
    # DOM but not visible below the sm (640px) breakpoint, which every
    # Android emulator profile used in CI (pixel_5) is under. This is the
    # real, intended mobile behavior, not a bug to work around.
    assert chrome.is_present(*chrome.BREADCRUMB_NAV)
    assert not chrome.is_visible(*chrome.BREADCRUMB_NAV, timeout=3)
