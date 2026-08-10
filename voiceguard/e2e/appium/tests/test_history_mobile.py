"""Mobile-web coverage of /history (frontend/src/pages/History/index.tsx).

Deliberately order-independent: does NOT assume the account has zero or
some scans (which real scan exists depends on whether
test_scan_flow_mobile.py's upload has run yet in this session — see that
file's docstring). Structural/interaction assertions only; the "a real
uploaded scan shows up here" assertion lives in test_scan_flow_mobile.py,
which is the one place that actually knows a scan was just created.
"""
from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.history_page import HistoryPage


def test_history_page_title_renders(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    assert page.find(By.TAG_NAME, "h1").text == "Scan history"


def test_history_shows_empty_state_or_table(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    assert page.is_showing_empty_state(timeout=5) or page.is_showing_table(timeout=5)


def test_history_new_scan_link_navigates_to_scan_new(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    page.tap(page.find_clickable(*page.NEW_SCAN_LINK))
    page.wait_url_contains("/scan/new")


def test_history_status_filter_defaults_to_all(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    if not page.is_showing_table(timeout=5):
        return  # EmptyHistory replaces the whole card, incl. the filter — nothing to assert.
    select_el = page.find(*page.STATUS_FILTER)
    assert select_el.get_attribute("value") == "all"


def test_history_status_filter_can_be_changed(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    if not page.is_showing_table(timeout=5):
        return
    page.select_status_filter("completed")
    assert page.find(*page.STATUS_FILTER).get_attribute("value") == "completed"
    page.select_status_filter("all")  # leave it as found for any test that runs after this one
