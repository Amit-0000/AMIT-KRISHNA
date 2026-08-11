"""Desktop accessibility coverage.

Every selector/assertion here is grounded in real, read source (not
guessed): the shared authenticated shell (frontend/src/components/layout/
AppShell.tsx) renders a real `motion.main id="main-content"` landmark
(framer-motion's `motion.main` is a genuine `<main>` element) plus a
`skip to main content` link, for every route it wraps -- confirmed by
reading AppShell.tsx directly. Icon-only chrome buttons' aria-labels are
the same ones pages/nav.py already drives (HAMBURGER, DESKTOP_SEARCH_TRIGGER,
NOTIFICATION_BELL, THEME_TOGGLE_ICON, Sidebar.COLLAPSE_TOGGLE). Login/Signup
label associations are read from Login/index.tsx and Signup/index.tsx's real
<Label htmlFor=...> markup.
"""
from __future__ import annotations

import uuid

import pytest
from selenium.webdriver.common.by import By

from data.users import FIXTURE_USER
from pages.base_page import BasePage
from pages.help_feedback_pages import FeedbackPage, HelpCenterPage
from pages.history_page import HistoryPage
from pages.nav import AppChrome, Sidebar
from pages.notifications_page import NotificationsPage
from pages.scan_pages import NewScanPage
from pages.settings_pages import SETTINGS_TABS_NAV, AppearancePage

pytestmark = [pytest.mark.medium]

MAIN_LANDMARK = (By.CSS_SELECTOR, "main#main-content")
SKIP_LINK = (By.CSS_SELECTOR, 'a[href="#main-content"]')

AUTHENTICATED_ROUTES = [
    "/dashboard",
    "/history",
    "/notifications",
    "/help",
    "/feedback",
    "/scan/new",
    "/settings/profile",
    "/settings/account",
    "/settings/appearance",
]


@pytest.mark.parametrize("route", AUTHENTICATED_ROUTES)
def test_authenticated_route_has_main_landmark(authenticated_driver, base_url, route):
    page = BasePage(authenticated_driver, base_url)
    page.goto(route)
    assert page.is_present(*MAIN_LANDMARK), f"{route} should render AppShell's main#main-content landmark"


@pytest.mark.parametrize("route", AUTHENTICATED_ROUTES)
def test_authenticated_route_has_skip_to_content_link(authenticated_driver, base_url, route):
    page = BasePage(authenticated_driver, base_url)
    page.goto(route)
    assert page.is_present(*SKIP_LINK), f"{route} should render AppShell's skip-to-content link"


def test_landing_page_has_main_landmark(driver, base_url):
    page = BasePage(driver, base_url)
    page.goto("/")
    assert page.is_present(By.TAG_NAME, "main")


def test_shared_result_page_has_main_landmark(driver, base_url):
    page = BasePage(driver, base_url)
    page.goto(f"/r/{uuid.uuid4()}")
    assert page.is_present(By.TAG_NAME, "main")


def test_hamburger_button_has_aria_label(authenticated_driver, base_url):
    # TopBar's hamburger is `lg:hidden` -- present in the DOM but not
    # `visibility_of_element_located`-visible at this suite's 1440x900
    # desktop viewport (test_navigation.py's test_hamburger_hidden_on_
    # desktop_viewport already covers exactly this), so this must query the
    # DOM directly rather than use BasePage.find()'s visibility wait.
    chrome = AppChrome(authenticated_driver, base_url)
    chrome.goto("/dashboard")
    hamburgers = chrome.driver.find_elements(*chrome.HAMBURGER)
    assert hamburgers and hamburgers[0].get_attribute("aria-label") == "Open navigation"


def test_search_trigger_has_aria_label(authenticated_driver, base_url):
    chrome = AppChrome(authenticated_driver, base_url)
    chrome.goto("/dashboard")
    assert chrome.find(*chrome.DESKTOP_SEARCH_TRIGGER).get_attribute("aria-label")


def test_notification_bell_has_aria_label(authenticated_driver, base_url):
    chrome = AppChrome(authenticated_driver, base_url)
    chrome.goto("/dashboard")
    label = chrome.find(*chrome.NOTIFICATION_BELL).get_attribute("aria-label")
    assert label and label.startswith("Notifications")


def test_theme_toggle_has_aria_label(authenticated_driver, base_url):
    chrome = AppChrome(authenticated_driver, base_url)
    chrome.goto("/dashboard")
    label = chrome.find(*chrome.THEME_TOGGLE_ICON).get_attribute("aria-label")
    assert label and label.startswith("Current theme")


def test_sidebar_collapse_toggle_has_aria_label(authenticated_driver, base_url):
    sidebar = Sidebar(authenticated_driver, base_url)
    sidebar.goto("/dashboard")
    label = sidebar.find(*sidebar.COLLAPSE_TOGGLE).get_attribute("aria-label")
    assert label in ("Collapse sidebar", "Expand sidebar")


def test_sidebar_aside_has_aria_label(authenticated_driver, base_url):
    sidebar = Sidebar(authenticated_driver, base_url)
    sidebar.goto("/dashboard")
    assert sidebar.find(*sidebar.ASIDE).get_attribute("aria-label") == "Main navigation"


def test_sidebar_nav_has_aria_label(authenticated_driver, base_url):
    sidebar = Sidebar(authenticated_driver, base_url)
    sidebar.goto("/dashboard")
    assert sidebar.find(*sidebar.NAV_LANDMARK).get_attribute("aria-label") == "Sidebar navigation"


def test_login_email_input_has_associated_label(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/login")
    label = page.find(By.CSS_SELECTOR, 'label[for="email"]')
    assert label.text.strip() == "Email"


def test_login_password_input_has_associated_label(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/login")
    label = page.find(By.CSS_SELECTOR, 'label[for="password"]')
    assert label.text.strip() == "Password"


def test_signup_display_name_input_has_associated_label(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/signup")
    label = page.find(By.CSS_SELECTOR, 'label[for="displayName"]')
    assert label.text.strip() == "Display name"


def test_signup_confirm_password_input_has_associated_label(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/signup")
    label = page.find(By.CSS_SELECTOR, 'label[for="confirmPassword"]')
    assert label.text.strip() == "Confirm password"


def test_global_search_dialog_has_aria_label(authenticated_driver, base_url):
    chrome = AppChrome(authenticated_driver, base_url)
    chrome.goto("/dashboard")
    search = chrome.open_search()
    assert search.find(*search.DIALOG).get_attribute("aria-label") == "Search"
    search.close()


def test_global_search_input_has_aria_label(authenticated_driver, base_url):
    chrome = AppChrome(authenticated_driver, base_url)
    chrome.goto("/dashboard")
    search = chrome.open_search()
    assert search.find(*search.INPUT).get_attribute("aria-label") == "Search VoiceGuard"
    search.close()


def test_notification_panel_has_aria_label(authenticated_driver, base_url):
    chrome = AppChrome(authenticated_driver, base_url)
    chrome.goto("/dashboard")
    panel = chrome.open_notifications()
    assert panel.find(*panel.PANEL).get_attribute("aria-label") == "Notifications"
    panel.close()


def test_history_table_has_aria_label(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    if not page.is_showing_table(timeout=5):
        pytest.skip("fixture account currently has zero scans -- no table to check")
    assert page.find(*page.TABLE).get_attribute("aria-label") == "Scan history"


def test_notifications_tablist_has_aria_label(authenticated_driver, base_url):
    page = NotificationsPage(authenticated_driver, base_url)
    page.goto_notifications()
    assert page.find(*page.TABLIST).get_attribute("aria-label") == "Filter notifications"


def test_breadcrumb_nav_has_aria_label(authenticated_driver, base_url):
    chrome = AppChrome(authenticated_driver, base_url)
    chrome.goto("/dashboard")
    assert chrome.find(*chrome.BREADCRUMB_NAV).get_attribute("aria-label") == "Breadcrumb"


def test_appearance_theme_radiogroup_has_aria_label(authenticated_driver, base_url):
    page = AppearancePage(authenticated_driver, base_url)
    page.goto_appearance()
    assert page.find(*page.THEME_RADIOGROUP).get_attribute("aria-label") == "Theme"


def test_feedback_category_radiogroup_has_aria_label(authenticated_driver, base_url):
    page = FeedbackPage(authenticated_driver, base_url)
    page.goto_feedback()
    assert page.find(*page.CATEGORY_RADIOGROUP).get_attribute("aria-label") == "Feedback category"


def test_new_scan_dropzone_has_button_role(authenticated_driver, base_url):
    page = NewScanPage(authenticated_driver, base_url)
    page.goto_new_scan()
    assert page.find(*page.DROPZONE).get_attribute("role") == "button"


def test_help_search_input_has_aria_label(authenticated_driver, base_url):
    page = HelpCenterPage(authenticated_driver, base_url)
    page.goto_help()
    assert page.find(*page.SEARCH_INPUT).get_attribute("aria-label") == "Search help articles"


def test_history_status_filter_has_associated_label(authenticated_driver, base_url):
    # EmptyHistory replaces the whole card, including the filter, when the
    # account has zero scans yet -- same real, order-dependent state
    # test_history.py's own tests already guard for (this suite's fixture
    # account may or may not have a scan yet depending on whether
    # test_scan_flow.py's single real upload has run first).
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    if not page.is_showing_table(timeout=5):
        pytest.skip("fixture account currently has zero scans -- no status filter to check")
    label = page.find(By.CSS_SELECTOR, 'label[for="scan-status-filter"]')
    assert label is not None


def test_user_menu_has_menu_role(authenticated_driver, base_url):
    sidebar = Sidebar(authenticated_driver, base_url)
    sidebar.goto("/dashboard")
    menu = sidebar.open_user_menu(FIXTURE_USER["display_name"])
    assert menu.find(*menu.MENU).get_attribute("role") == "menu"


def test_user_menu_items_have_menuitem_role(authenticated_driver, base_url):
    sidebar = Sidebar(authenticated_driver, base_url)
    sidebar.goto("/dashboard")
    menu = sidebar.open_user_menu(FIXTURE_USER["display_name"])
    assert menu.find(*menu.PROFILE_ITEM).get_attribute("role") == "menuitem"
    assert menu.find(*menu.ACCOUNT_ITEM).get_attribute("role") == "menuitem"


def test_forgot_password_email_input_has_associated_label(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/forgot-password")
    label = page.find(By.CSS_SELECTOR, 'label[for="email"]')
    assert label.text.strip() == "Email"


def test_reset_password_input_has_associated_label(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/reset-password?token=any-nonempty-token-value")
    label = page.find(By.CSS_SELECTOR, 'label[for="password"]')
    assert label.text.strip() == "New password"


def test_profile_display_name_input_has_associated_label(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.goto("/settings/profile")
    label = page.find(By.CSS_SELECTOR, 'label[for="displayName"]')
    assert label is not None


def test_feedback_message_textarea_has_associated_label(authenticated_driver, base_url):
    page = FeedbackPage(authenticated_driver, base_url)
    page.goto_feedback()
    label = page.find(By.CSS_SELECTOR, 'label[for="message"]')
    assert label is not None


def test_settings_tabs_nav_has_aria_label(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.goto("/settings/profile")
    assert page.find(*SETTINGS_TABS_NAV).get_attribute("aria-label") == "Settings sections"


def test_scan_history_new_scan_link_is_a_real_anchor(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    link = page.find(*page.NEW_SCAN_LINK)
    assert link.tag_name == "a"
    assert link.get_attribute("href").endswith("/scan/new")
