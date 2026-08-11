"""Desktop coverage of the shared app chrome: Sidebar, GlobalSearch,
NotificationCenter, UserMenu, ThemeToggle, Breadcrumb.

Headless Chrome here runs at 1440x900 (conftest.py), a `lg`+`sm` viewport —
the opposite of the Appium mobile suite's emulator profile. That means
Sidebar and Breadcrumb actually render here (both `hidden` below their
breakpoints on mobile), while the hamburger/MobileDrawer path does not
(`lg:hidden`). All of this chrome only renders inside AppShell (authenticated
routes), so every test here starts from a real, already-authenticated
/dashboard view.
"""
from __future__ import annotations

import pytest

from data.users import FIXTURE_USER
from pages.dashboard_page import DashboardPage
from pages.nav import AppChrome, GlobalSearch, NotificationCenter, Sidebar, UserMenu

pytestmark = [pytest.mark.medium]


@pytest.fixture
def chrome(authenticated_driver, base_url):
    DashboardPage(authenticated_driver, base_url).goto_dashboard()
    return AppChrome(authenticated_driver, base_url)


@pytest.fixture
def sidebar(authenticated_driver, base_url):
    DashboardPage(authenticated_driver, base_url).goto_dashboard()
    return Sidebar(authenticated_driver, base_url)


def test_sidebar_visible_on_desktop_viewport(sidebar):
    assert sidebar.is_visible(*sidebar.ASIDE, timeout=5)


def test_hamburger_hidden_on_desktop_viewport(chrome):
    # TopBar.tsx renders the mobile hamburger with `lg:hidden` -- present in
    # the DOM but not visible at this viewport's >=1024px width. Real,
    # intended desktop behavior, the mirror image of the Appium suite's
    # "breadcrumb hidden on mobile" test.
    assert chrome.is_present(*chrome.HAMBURGER)
    assert not chrome.is_visible(*chrome.HAMBURGER, timeout=3)


def test_breadcrumb_visible_on_desktop_viewport(chrome):
    assert chrome.is_visible(*chrome.BREADCRUMB_NAV, timeout=5)


def test_breadcrumb_shows_dashboard_root_and_current_page(chrome):
    chrome.goto("/history")
    chrome.wait_url_contains("/history")
    assert chrome.breadcrumb_labels() == ["Dashboard", "History"]


def test_sidebar_dashboard_link_active_on_dashboard(sidebar):
    assert sidebar.is_link_active("Dashboard")


def test_sidebar_history_link_navigates(sidebar):
    sidebar.go_to("History")
    sidebar.wait_url_contains("/history")
    assert "/history" in sidebar.current_url


def test_sidebar_new_scan_link_navigates(sidebar):
    sidebar.go_to("New Scan")
    sidebar.wait_url_contains("/scan/new")
    assert "/scan/new" in sidebar.current_url


def test_sidebar_help_center_link_navigates(sidebar):
    sidebar.go_to("Help Center")
    sidebar.wait_url_contains("/help")
    assert "/help" in sidebar.current_url


def test_sidebar_give_feedback_link_navigates(sidebar):
    sidebar.go_to("Give Feedback")
    sidebar.wait_url_contains("/feedback")
    assert "/feedback" in sidebar.current_url


def test_sidebar_settings_link_navigates(sidebar):
    sidebar.go_to_settings()
    sidebar.wait_url_contains("/settings")
    assert "/settings" in sidebar.current_url


def test_sidebar_collapse_toggle_collapses_and_expands(sidebar):
    assert not sidebar.is_collapsed()
    sidebar.toggle_collapse()
    assert sidebar.is_collapsed()
    sidebar.toggle_collapse()
    assert not sidebar.is_collapsed()


def test_user_menu_opens_from_sidebar_and_shows_account_links(sidebar):
    menu = sidebar.open_user_menu(FIXTURE_USER["display_name"])
    assert menu.is_open()
    assert menu.find(*menu.PROFILE_ITEM).is_displayed()
    assert menu.find(*menu.ACCOUNT_ITEM).is_displayed()


def test_user_menu_profile_link_navigates_to_settings_profile(sidebar):
    menu = sidebar.open_user_menu(FIXTURE_USER["display_name"])
    menu.go_to_profile()
    menu.wait_url_contains("/settings/profile")
    assert "/settings/profile" in menu.current_url


def test_global_search_opens_via_desktop_trigger(chrome):
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
    # wait_gone, not an instant is_open() check: handleSelect calls close()
    # (setOpen(false)) synchronously before navigate(), but GlobalSearch.tsx
    # wraps the dialog in AnimatePresence with a real 0.18s exit transition
    # -- the element stays mounted (and still Selenium-"visible", since
    # opacity/scale mid-transition isn't display:none) for that window.
    # GlobalSearch.close() already uses wait_gone for exactly this reason;
    # this assertion needs the same pattern.
    search.wait_gone(*search.DIALOG)


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


def test_sidebar_collapse_state_persists_across_navigation(sidebar):
    # uiStore.ts persists sidebarCollapsed to localStorage -- its starting
    # value here depends on whatever an earlier test in this run last left
    # it as (e.g. test_sidebar_collapse_toggle_and_expands's own toggle
    # pair), not necessarily "expanded". Capture the real starting state
    # instead of assuming one.
    started_collapsed = sidebar.is_collapsed()
    sidebar.toggle_collapse()
    assert sidebar.is_collapsed() != started_collapsed
    sidebar.go_to("History")
    sidebar.wait_url_contains("/history")
    assert sidebar.is_collapsed() != started_collapsed, "collapsed sidebar state should survive an in-app navigation"
    sidebar.toggle_collapse()  # leave it as found for tests that run after this one
    assert sidebar.is_collapsed() == started_collapsed


def test_sidebar_notifications_link_navigates(sidebar):
    sidebar.go_to("Notifications")
    sidebar.wait_url_contains("/notifications")
    assert "/notifications" in sidebar.current_url


def test_sidebar_dashboard_link_navigates_back_from_another_page(sidebar):
    sidebar.go_to("History")
    sidebar.wait_url_contains("/history")
    sidebar.go_to("Dashboard")
    sidebar.wait_url_contains("/dashboard")
    assert "/dashboard" in sidebar.current_url


def test_sidebar_history_link_active_on_history_page(sidebar):
    sidebar.go_to("History")
    sidebar.wait_url_contains("/history")
    assert sidebar.is_link_active("History")
    assert not sidebar.is_link_active("Dashboard")


def test_breadcrumb_shows_settings_section_on_settings_pages(chrome):
    chrome.goto("/settings/profile")
    chrome.wait_url_contains("/settings/profile")
    labels = chrome.breadcrumb_labels()
    assert labels and labels[0] == "Dashboard"
    assert "Settings" in labels or "Profile" in labels


def test_user_menu_appearance_link_navigates_to_settings_appearance(sidebar):
    menu = sidebar.open_user_menu(FIXTURE_USER["display_name"])
    menu.click(menu.find_clickable(*menu.APPEARANCE_ITEM))
    menu.wait_url_contains("/settings/appearance")
    assert "/settings/appearance" in menu.current_url


def test_user_menu_account_link_navigates_to_settings_account(sidebar):
    menu = sidebar.open_user_menu(FIXTURE_USER["display_name"])
    menu.click(menu.find_clickable(*menu.ACCOUNT_ITEM))
    menu.wait_url_contains("/settings/account")
    assert "/settings/account" in menu.current_url


def test_global_search_result_labels_include_settings(chrome):
    search = chrome.open_search()
    search.type_query("settings")
    labels = search.result_labels()
    assert any("Settings" in label for label in labels)
    search.close()


def test_global_search_input_clears_between_openings(chrome):
    search = chrome.open_search()
    search.type_query("history")
    search.close()
    reopened = chrome.open_search()
    assert reopened.find(*reopened.INPUT).get_attribute("value") == ""
    reopened.close()


def test_notification_center_panel_has_dialog_role_for_assistive_tech(chrome):
    panel = chrome.open_notifications()
    assert panel.find(*panel.PANEL).get_attribute("role") == "dialog"
    panel.close()
