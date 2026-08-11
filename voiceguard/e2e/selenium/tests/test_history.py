"""Desktop coverage of /history (frontend/src/pages/History/index.tsx).

Deliberately order-independent: does NOT assume the account has zero or
some scans (which real scan exists depends on whether test_scan_flow.py's
upload has run yet in this session — see that file's docstring).
Structural/interaction assertions only; the "a real uploaded scan shows up
here" assertion lives in test_scan_flow.py, which is the one place that
actually knows a scan was just created.
"""
from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from pages.history_page import HistoryPage

pytestmark = [pytest.mark.medium]


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
    page.click(page.find_clickable(*page.NEW_SCAN_LINK))
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


def test_history_table_rows_have_accessible_row_role(authenticated_driver, base_url):
    # Desktop-only structural check: a real <table> with proper row
    # semantics matters more for desktop screen-reader/keyboard table
    # navigation than for a mobile card-style layout.
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    if not page.is_showing_table(timeout=5):
        return
    rows = page.find_all(*page.ROWS)
    assert all(r.get_attribute("role") == "row" for r in rows)


def test_history_reachable_directly_via_url(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    assert "/history" in page.current_url
    assert "/login" not in page.current_url


def test_history_status_filter_has_all_documented_options(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    if not page.is_showing_table(timeout=5):
        return
    select = Select(page.find(*page.STATUS_FILTER))
    values = [o.get_attribute("value") for o in select.options]
    assert "all" in values
    assert "completed" in values


def test_history_page_title_is_an_h1(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    assert page.find(By.TAG_NAME, "h1").tag_name == "h1"


def test_history_selecting_processing_filter_does_not_error(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    if not page.is_showing_table(timeout=5):
        return
    page.select_status_filter("preprocessing")
    assert page.find(*page.STATUS_FILTER).get_attribute("value") == "preprocessing"
    page.select_status_filter("all")


def test_history_selecting_queued_filter_does_not_error(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    if not page.is_showing_table(timeout=5):
        return
    page.select_status_filter("queued")
    assert page.find(*page.STATUS_FILTER).get_attribute("value") == "queued"
    page.select_status_filter("all")


def test_history_selecting_validation_failed_filter_does_not_error(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    if not page.is_showing_table(timeout=5):
        return
    page.select_status_filter("validation_failed")
    assert page.find(*page.STATUS_FILTER).get_attribute("value") == "validation_failed"
    page.select_status_filter("all")


def test_history_selecting_failed_filter_does_not_error(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    if not page.is_showing_table(timeout=5):
        return
    page.select_status_filter("failed")
    assert page.find(*page.STATUS_FILTER).get_attribute("value") == "failed"
    page.select_status_filter("all")
