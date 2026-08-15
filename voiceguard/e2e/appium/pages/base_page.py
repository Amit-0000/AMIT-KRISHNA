"""Shared helpers for the mobile-web Page Object Model.

All page objects drive the same Appium `driver` fixture from ../conftest.py
(UiAutomator2 + real mobile Chrome), so this base wraps Selenium's
WebDriverWait/EC calls once instead of every page object re-writing them.
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

    # ── interaction (touch, via mobile Chrome's DOM — real tap events are
    # dispatched by UiAutomator2 under the hood on .click()) ──────────────
    def tap(self, element: WebElement) -> None:
        element.click()

    def tap_id(self, element_id: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        # CSS_SELECTOR, not By.ID: Appium's locator converter passes
        # locators through unchanged (unlike plain Selenium, which rewrites
        # By.ID to a CSS selector) — chromedriver rejects a raw "id"
        # strategy as invalid under W3C WebDriver.
        self.tap(self.find_clickable(By.CSS_SELECTOR, f"#{element_id}", timeout=timeout))

    def type_text(self, element: WebElement, text: str) -> None:
        element.clear()
        element.send_keys(text)

    def fill_id(self, element_id: str, text: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        # See tap_id above for why CSS_SELECTOR, not By.ID.
        self.type_text(self.find(By.CSS_SELECTOR, f"#{element_id}", timeout=timeout), text)

    def scroll_to_bottom(self) -> None:
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def scroll_into_view(self, element: WebElement) -> None:
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

    # ── content helpers ─────────────────────────────────────────────────
    def body_text(self) -> str:
        return self.find(By.TAG_NAME, "body").text

    def alert_text(self, timeout: int = DEFAULT_TIMEOUT) -> str:
        return self.find(By.CSS_SELECTOR, "[role=alert]", timeout=timeout).text

    def submit(self) -> None:
        self.tap(self.find_clickable(By.CSS_SELECTOR, "button[type=submit]"))
