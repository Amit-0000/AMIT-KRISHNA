"""Page object for /notifications (frontend/src/pages/Notifications/index.tsx)."""
from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import DEFAULT_TIMEOUT, BasePage


class NotificationsPage(BasePage):
    TABLIST = (By.CSS_SELECTOR, "[role=tablist][aria-label='Filter notifications']")
    ALL_TAB = (By.XPATH, "//button[@role='tab'][normalize-space()='All']")
    UNREAD_TAB = (By.XPATH, "//button[@role='tab'][starts-with(normalize-space(), 'Unread')]")
    READ_TAB = (By.XPATH, "//button[@role='tab'][normalize-space()='Read']")
    EMPTY_HEADINGS = (
        By.XPATH,
        "//h2[contains(text(), 'No notifications yet') or contains(text(), \"You're all caught up\") "
        "or contains(text(), 'No read notifications')]",
    )

    def goto_notifications(self) -> None:
        self.goto("/notifications")

    def is_loaded(self, timeout: int = DEFAULT_TIMEOUT) -> bool:
        return self.is_visible(*self.TABLIST, timeout=timeout)

    def select_tab(self, by_locator) -> None:
        self.click(self.find_clickable(*by_locator))

    def is_tab_selected(self, by_locator) -> bool:
        el = self.find(*by_locator)
        return el.get_attribute("aria-selected") == "true"
