"""Shared helpers for the desktop Selenium Page Object Model.

All page objects drive the same `driver` fixture from ../conftest.py
(headless Chrome). Adapted from voiceguard/e2e/appium/pages/base_page.py —
same shape, minus the mobile-Chrome-via-Appium-specific naming (tap ->
click), plus a couple of genuinely desktop-only helpers (resize_window,
send_keys_to_active_element) the mobile suite has no equivalent use for.
"""
from __future__ import annotations

from typing import Callable, TypeVar

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_TIMEOUT = 15

T = TypeVar("T")


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
    def _retry_on_stale(self, locate_and_act: Callable[[], T], attempts: int = 2) -> T:
        """Re-locates and retries once on StaleElementReferenceException.

        Confirmed live (both locally and in CI): the app runs under
        `npm run dev` (Vite) with React's <StrictMode> (frontend/src/main.tsx)
        wrapping the whole tree, which in development intentionally
        re-invokes the initial render/effects immediately after first mount.
        A `find()` that resolves against the first pass can occasionally have
        its element replaced a beat later by the time the very next WebDriver
        command reaches it, throwing StaleElementReferenceException even
        though `find()`'s own visibility/clickability wait already succeeded.
        This is a dev-server/StrictMode-only artifact, not a production
        behavior or an app bug (see the reasoning trail in
        test_error_handling.py's extremely-long-input tests, where this was
        first isolated). `locate_and_act` must re-locate the element itself
        each call (not close over an already-found WebElement) so the retry
        gets a fresh reference rather than reusing the one that just went
        stale.
        """
        last_exc: StaleElementReferenceException | None = None
        for _ in range(attempts):
            try:
                return locate_and_act()
            except StaleElementReferenceException as exc:
                last_exc = exc
        assert last_exc is not None
        raise last_exc

    def click(self, element: WebElement) -> None:
        element.click()

    def click_id(self, element_id: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        self._retry_on_stale(lambda: self.click(self.find_clickable(By.ID, element_id, timeout=timeout)))

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
        self._retry_on_stale(lambda: self.type_text(self.find(By.ID, element_id, timeout=timeout), text))

    def set_value_js(self, element: WebElement, text: str) -> None:
        """Sets an input's value via the native value setter + a dispatched
        'input'/'change' event, instead of simulating one keystroke per
        character over the wire.

        Only meant for pathologically long stress-test strings (hundreds to
        thousands of characters — see test_error_handling.py's extremely-
        long-input cases): send_keys()-ing thousands of real characters one
        at a time is needlessly slow (multiple seconds) for a value that's
        realistically arriving as a paste anyway, not real typing. Using the
        native HTMLInputElement.prototype 'value' setter (rather than plain
        `el.value = text`) is what's needed for React's synthetic event
        system to register the change from a JS-set value.
        """
        self.driver.execute_script(
            "const el = arguments[0], val = arguments[1];"
            "const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;"
            "setter.call(el, val);"
            "el.dispatchEvent(new Event('input', { bubbles: true }));"
            "el.dispatchEvent(new Event('change', { bubbles: true }));",
            element,
            text,
        )

    def fill_id_fast(self, element_id: str, text: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        self._retry_on_stale(lambda: self.set_value_js(self.find(By.ID, element_id, timeout=timeout), text))

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

    def body_contains(self, *substrings: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        """Polls body text for any of the given substrings instead of a single
        immediate read. Confirmed live: a bare `substring in self.body_text()`
        called right after navigation races the app's async client-side
        determination of which message to show (e.g. ResetPasswordPage
        deciding "invalid/expired" vs. the real form) — the body element
        itself is visible almost immediately on page load, well before that
        determination has rendered, so a one-shot read can catch the page
        mid-render and see neither expected string yet."""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: any(s in d.find_element(By.TAG_NAME, "body").text for s in substrings)
            )
            return True
        except TimeoutException:
            return False

    def alert_text(self, timeout: int = DEFAULT_TIMEOUT) -> str:
        return self.find(By.CSS_SELECTOR, "[role=alert]", timeout=timeout).text

    def submit(self) -> None:
        self._retry_on_stale(lambda: self.click(self.find_clickable(By.CSS_SELECTOR, "button[type=submit]")))
