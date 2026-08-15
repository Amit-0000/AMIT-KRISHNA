"""Page object for /history (frontend/src/pages/History/index.tsx +
components/ScanHistoryTable.tsx, components/EmptyHistory.tsx)."""
from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import DEFAULT_TIMEOUT, BasePage


class HistoryPage(BasePage):
    EMPTY_STATE = (By.CSS_SELECTOR, "[aria-label='No scans yet']")
    TABLE = (By.CSS_SELECTOR, "table[aria-label='Scan history']")
    # CSS_SELECTOR, not By.ID: Appium's locator converter passes locators
    # through unchanged, and chromedriver rejects a raw "id" strategy as
    # invalid under W3C WebDriver (see pages/base_page.py's tap_id).
    STATUS_FILTER = (By.CSS_SELECTOR, "#scan-status-filter")
    NEW_SCAN_LINK = (By.LINK_TEXT, "New scan")
    ROWS = (By.CSS_SELECTOR, "table[aria-label='Scan history'] tbody tr[role=row]")

    def goto_history(self) -> None:
        self.goto("/history")

    def is_showing_empty_state(self, timeout: int = DEFAULT_TIMEOUT) -> bool:
        return self.is_visible(*self.EMPTY_STATE, timeout=timeout)

    def is_showing_table(self, timeout: int = DEFAULT_TIMEOUT) -> bool:
        return self.is_visible(*self.TABLE, timeout=timeout)

    def row_for_filename(self, filename: str):
        # ScanRow's aria-label is f"{original_filename} — {status}" — a
        # substring match on the filename is real and stable regardless of
        # current status.
        return self.find(By.XPATH, f"//tr[contains(@aria-label, \"{filename}\")]")

    def select_status_filter(self, value: str) -> None:
        from selenium.webdriver.support.ui import Select

        Select(self.find(*self.STATUS_FILTER)).select_by_value(value)
