"""Desktop coverage of /notifications (frontend/src/pages/Notifications/index.tsx).
Tab-switching is real, order-independent interaction coverage — doesn't
assume any notification data exists (loading/error/empty/populated all
render the same tablist)."""
from __future__ import annotations

import pytest

from pages.notifications_page import NotificationsPage

pytestmark = [pytest.mark.medium]


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


def test_notifications_tabs_have_tab_role_for_assistive_tech(authenticated_driver, base_url):
    page = NotificationsPage(authenticated_driver, base_url)
    page.goto_notifications()
    for tab in (page.ALL_TAB, page.UNREAD_TAB, page.READ_TAB):
        assert page.find(*tab).get_attribute("role") == "tab"


def test_notifications_tablist_has_tablist_role(authenticated_driver, base_url):
    page = NotificationsPage(authenticated_driver, base_url)
    page.goto_notifications()
    assert page.find(*page.TABLIST).get_attribute("role") == "tablist"


def test_notifications_page_reachable_directly_via_url(authenticated_driver, base_url):
    page = NotificationsPage(authenticated_driver, base_url)
    page.goto_notifications()
    assert "/notifications" in page.current_url
    assert "/login" not in page.current_url


def test_notifications_switching_tabs_does_not_change_url(authenticated_driver, base_url):
    # NotificationsPage filters client-side (no route change per tab) —
    # confirmed real behavior, not assumed.
    page = NotificationsPage(authenticated_driver, base_url)
    page.goto_notifications()
    before = page.current_url
    page.select_tab(page.UNREAD_TAB)
    assert page.current_url == before
    page.select_tab(page.ALL_TAB)


def test_notifications_unread_tab_label_starts_with_unread(authenticated_driver, base_url):
    page = NotificationsPage(authenticated_driver, base_url)
    page.goto_notifications()
    label = page.find(*page.UNREAD_TAB).text.strip()
    assert label.startswith("Unread")


def test_notifications_page_survives_switching_tabs_twice(authenticated_driver, base_url):
    page = NotificationsPage(authenticated_driver, base_url)
    page.goto_notifications()
    page.select_tab(page.UNREAD_TAB)
    page.select_tab(page.READ_TAB)
    page.select_tab(page.ALL_TAB)
    assert page.is_tab_selected(page.ALL_TAB)


def test_notifications_only_one_tab_selected_at_a_time(authenticated_driver, base_url):
    page = NotificationsPage(authenticated_driver, base_url)
    page.goto_notifications()
    page.select_tab(page.UNREAD_TAB)
    selected = [
        t for t in (page.ALL_TAB, page.UNREAD_TAB, page.READ_TAB) if page.is_tab_selected(t)
    ]
    assert len(selected) == 1
    page.select_tab(page.ALL_TAB)
