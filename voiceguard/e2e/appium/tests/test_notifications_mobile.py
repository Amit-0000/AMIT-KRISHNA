"""Mobile-web coverage of /notifications
(frontend/src/pages/Notifications/index.tsx). Tab-switching is real,
order-independent interaction coverage — doesn't assume any notification
data exists (loading/error/empty/populated all render the same tablist)."""
from __future__ import annotations

from pages.notifications_page import NotificationsPage


def test_notifications_page_shows_filter_tabs(authenticated_driver, base_url):
    page = NotificationsPage(authenticated_driver, base_url)
    page.goto_notifications()
    assert page.is_loaded()


def test_notifications_all_tab_selected_by_default(authenticated_driver, base_url):
    page = NotificationsPage(authenticated_driver, base_url)
    page.goto_notifications()
    assert page.is_tab_selected(page.ALL_TAB)


def test_notifications_can_switch_to_unread_tab(authenticated_driver, base_url):
    page = NotificationsPage(authenticated_driver, base_url)
    page.goto_notifications()
    page.select_tab(page.UNREAD_TAB)
    assert page.is_tab_selected(page.UNREAD_TAB)
    assert not page.is_tab_selected(page.ALL_TAB)


def test_notifications_can_switch_to_read_tab(authenticated_driver, base_url):
    page = NotificationsPage(authenticated_driver, base_url)
    page.goto_notifications()
    page.select_tab(page.READ_TAB)
    assert page.is_tab_selected(page.READ_TAB)
    page.select_tab(page.ALL_TAB)  # leave it as found
