"""Shared helpers for the desktop Selenium Page Object Model.

All page objects drive the same `driver` fixture from ../conftest.py
(headless Chrome). Adapted from voiceguard/e2e/appium/pages/base_page.py —
same shape, minus the mobile-Chrome-via-Appium-specific naming (tap ->
click), plus a couple of genuinely desktop-only helpers (resize_window,
send_keys_to_active_element) the mobile suite has no equivalent use for.
"""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_TIMEOUT = 15


class BasePage:
    def __init__(self, driver, base_url: str):
        self.driver = driver
        self.base_url = base_url

    # ── navigation ──────────────────────────────────────────────────────
    def goto(self, path: str) -> None:
        self.driver.get(f"{self.base_url}{path}")

    @property
    def current_url(self) -> str:
        return self.driver.current_url

    def wait_url_contains(self, fragment: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        WebDriverWait(self.driver, timeout).until(EC.url_contains(fragment))

    # ── element access ──────────────────────────────────────────────────
    def find(self, by: str, value: str, timeout: int = DEFAULT_TIMEOUT) -> WebElement:
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )

    def find_clickable(self, by: str, value: str, timeout: int = DEFAULT_TIMEOUT) -> WebElement:
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )

    def find_all(self, by: str, value: str) -> list[WebElement]:
        return self.driver.find_elements(by, value)

    def is_present(self, by: str, value: str) -> bool:
        return len(self.driver.find_elements(by, value)) > 0

    def is_visible(self, by: str, value: str, timeout: int = 5) -> bool:
        try:
            self.find(by, value, timeout=timeout)
            return True
        except Exception:
            return False

    def wait_gone(self, by: str, value: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        WebDriverWait(self.driver, timeout).until(
            EC.invisibility_of_element_located((by, value))
        )

    # ── interaction ─────────────────────────────────────────────────────
    def click(self, element: WebElement) -> None:
        element.click()

    def click_id(self, element_id: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.click(self.find_clickable(By.ID, element_id, timeout=timeout))

    def js_click(self, element: WebElement) -> None:
        """Fallback for a real, reproducible issue found live: WebDriver's
        native coordinate-based click on some React Router <Link> elements
        (confirmed on Login's "Forgot password?" link) doesn't trigger
        client-side navigation in headless Chrome, even though the element
        is found correctly and nothing visually overlaps it — a JS-native
        `.click()` does. Use this only where a real navigate-on-click has
        been confirmed not to fire via the normal `click()`."""
        self.driver.execute_script("arguments[0].click();", element)

    def type_text(self, element: WebElement, text: str) -> None:
        element.clear()
        element.send_keys(text)

    def fill_id(self, element_id: str, text: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.type_text(self.find(By.ID, element_id, timeout=timeout), text)

    def scroll_to_bottom(self) -> None:
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def scroll_into_view(self, element: WebElement) -> None:
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

    def resize_window(self, width: int, height: int) -> None:
        self.driver.set_window_size(width, height)

    def send_keys_to_active_element(self, *keys) -> None:
        self.driver.switch_to.active_element.send_keys(*keys)

    def active_element_id(self) -> str | None:
        el = self.driver.switch_to.active_element
        return el.get_attribute("id") or None

    # ── content helpers ─────────────────────────────────────────────────
    def body_text(self) -> str:
        return self.find(By.TAG_NAME, "body").text

    def alert_text(self, timeout: int = DEFAULT_TIMEOUT) -> str:
        return self.find(By.CSS_SELECTOR, "[role=alert]", timeout=timeout).text

    def submit(self) -> None:
        self.click(self.find_clickable(By.CSS_SELECTOR, "button[type=submit]"))
