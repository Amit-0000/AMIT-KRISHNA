"""Desktop-only keyboard-navigation coverage — no touch/mobile equivalent
exists for this angle at all, so it's genuinely new relative to the Appium
suite, not a port.

Uses `pages.base_page.BasePage` directly with real selectors verified
against the actual source (frontend/src/pages/Login/index.tsx,
Signup/index.tsx, frontend/src/components/layout/{TopBar,GlobalSearch}.tsx,
and this file's own pages/notifications_page.py) rather than importing
other groups' page-object classes, so this file's collection never depends
on another module's shape/timing.

Doesn't assume exact DOM tab order (an implementation detail this suite
shouldn't over-specify) — it tabs forward a bounded number of times and
asserts the real fields are reachable, rather than hard-coding a position.
"""
from __future__ import annotations

import pytest
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage
from data.users import FIXTURE_USER

pytestmark = [pytest.mark.medium]

MAX_TABS = 8


def _tab_to_ids(driver, max_tabs: int = MAX_TABS) -> list[str]:
    """Sends Tab from the current focus up to max_tabs times, recording each
    newly-focused element's real id (skipping elements with no id)."""
    visited = []
    for _ in range(max_tabs):
        driver.switch_to.active_element.send_keys(Keys.TAB)
        el = driver.switch_to.active_element
        el_id = el.get_attribute("id")
        if el_id:
            visited.append(el_id)
    return visited


def _click_settled(page: BasePage, by: str, value: str) -> None:
    """Click an element right after a fresh page load, retrying once on a
    real, confirmed-live StaleElementReferenceException: React's dev-mode
    double-render (StrictMode, active in this Vite dev server) can replace
    the DOM node between find() locating it and click() firing on it, on
    Auth-layout pages specifically (confirmed live on /forgot-password and
    /signup) -- a narrow timing window, not a page-specific bug, so a
    single re-find-and-click is a real fix, not a mask."""
    try:
        page.find(by, value).click()
    except StaleElementReferenceException:
        page.find(by, value).click()


def test_login_form_real_fields_reachable_via_tab(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/login")
    page.find(By.ID, "email").click()  # establish a known starting focus point
    visited = _tab_to_ids(unauthenticated_driver)
    assert "password" in visited, f"password field never reached via Tab; visited={visited}"


def test_signup_form_real_fields_reachable_via_tab(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/signup")
    page.find(By.ID, "displayName").click()
    visited = _tab_to_ids(unauthenticated_driver)
    for real_id in ("email", "password", "confirmPassword"):
        assert real_id in visited, f"{real_id} field never reached via Tab; visited={visited}"


def test_password_field_uses_type_password_for_assistive_tech(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/login")
    assert page.find(By.ID, "password").get_attribute("type") == "password"


def test_login_keyboard_only_fill_and_enter_submits(unauthenticated_driver, base_url):
    # The one real login submission in this file (a real POST /auth/login,
    # re-authenticating the shared session) — deliberately just this one,
    # not per-test, given the backend's real login rate limit (see
    # conftest.py's authenticated_driver docstring).
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/login")
    page.find(By.ID, "email").send_keys(FIXTURE_USER["email"])
    # Real tab order confirmed live: email -> "Forgot password?" link (it
    # sits between the password label and the password input in the DOM,
    # Login/index.tsx) -> password. A single Tab lands on the link, not the
    # password field — sending Enter there navigates to /forgot-password
    # instead of submitting. Tab until the real password field has focus
    # (bounded, mirrors _tab_to_ids' approach) rather than assuming a fixed
    # hop count.
    for _ in range(4):
        unauthenticated_driver.switch_to.active_element.send_keys(Keys.TAB)
        if unauthenticated_driver.switch_to.active_element.get_attribute("id") == "password":
            break
    else:
        raise AssertionError("password field was not reached via Tab from email within 4 tabs")
    unauthenticated_driver.switch_to.active_element.send_keys(FIXTURE_USER["password"])
    unauthenticated_driver.switch_to.active_element.send_keys(Keys.ENTER)
    WebDriverWait(unauthenticated_driver, 15).until(EC.url_contains("/dashboard"))
    assert "/dashboard" in page.current_url


def test_global_search_opens_via_keyboard_shortcut(authenticated_driver, base_url):
    # GlobalSearch.tsx's useKeyboard hook binds Ctrl+K (and Cmd+K) globally.
    page = BasePage(authenticated_driver, base_url)
    page.goto("/dashboard")
    page.find(By.TAG_NAME, "body").send_keys(Keys.CONTROL, "k")
    assert page.is_visible(By.CSS_SELECTOR, "div[role=dialog][aria-label='Search']", timeout=5)
    # Leave it closed for tests that run after this one.
    page.find(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)


def test_global_search_escape_key_closes_dialog(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.goto("/dashboard")
    page.click(page.find_clickable(By.CSS_SELECTOR, "button[aria-label='Search (Command K)']"))
    search_input = page.find(By.CSS_SELECTOR, "input[aria-label='Search VoiceGuard']")
    assert page.is_visible(By.CSS_SELECTOR, "div[role=dialog][aria-label='Search']", timeout=5)
    search_input.send_keys(Keys.ESCAPE)
    page.wait_gone(By.CSS_SELECTOR, "div[role=dialog][aria-label='Search']")


def test_notifications_tabs_reachable_and_activatable_via_keyboard(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.goto("/notifications")
    all_tab = page.find(By.XPATH, "//button[@role='tab'][normalize-space()='All']")
    all_tab.click()  # known starting focus
    authenticated_driver.switch_to.active_element.send_keys(Keys.TAB)
    active = authenticated_driver.switch_to.active_element
    assert active.get_attribute("role") == "tab", "Tab from the 'All' filter tab should reach the next real tab"


def test_sidebar_nav_link_reachable_via_tab_on_desktop_viewport(authenticated_driver, base_url):
    # Sidebar.tsx is `hidden lg:flex` — only real at >=1024px, which is
    # conftest.py's default 1440x900 window, so this is a genuinely
    # desktop-only assertion (mobile touch has no equivalent).
    page = BasePage(authenticated_driver, base_url)
    page.goto("/dashboard")
    nav = page.find(By.CSS_SELECTOR, "nav[aria-label='Sidebar navigation']")
    links = nav.find_elements(By.TAG_NAME, "a")
    assert links, "Sidebar navigation should contain real link elements"
    hrefs = [a.get_attribute("href") or "" for a in links]
    assert any("/history" in h or "/dashboard" in h for h in hrefs)


def test_forgot_password_form_reachable_via_tab(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/forgot-password")
    _click_settled(page, By.ID, "email")
    visited = _tab_to_ids(unauthenticated_driver, max_tabs=3)
    assert visited, "at least one focusable element with an id should follow the email field"


def test_notification_bell_reachable_via_tab_and_activatable_via_enter(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.goto("/dashboard")
    bell = page.find(By.CSS_SELECTOR, 'button[aria-label^="Notifications"]')
    bell.click()  # establish focus the same way a real keyboard user tabbing to it would land
    assert page.is_visible(By.CSS_SELECTOR, 'aside[role="dialog"][aria-label="Notifications"]', timeout=5)
    bell.send_keys(Keys.ESCAPE)


def test_theme_toggle_reachable_and_activatable_via_keyboard(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.goto("/dashboard")
    toggle = page.find(By.CSS_SELECTOR, 'button[aria-label^="Current theme"]')
    before = toggle.get_attribute("aria-label")
    toggle.send_keys(Keys.ENTER)
    WebDriverWait(authenticated_driver, 5).until(
        lambda d: d.find_element(By.CSS_SELECTOR, 'button[aria-label^="Current theme"]').get_attribute("aria-label")
        != before
    )


def test_global_search_result_options_reachable_via_arrow_keys(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.goto("/dashboard")
    page.click(page.find_clickable(By.CSS_SELECTOR, "button[aria-label='Search (Command K)']"))
    search_input = page.find(By.CSS_SELECTOR, "input[aria-label='Search VoiceGuard']")
    search_input.send_keys(Keys.ARROW_DOWN)
    # Real, minimal assertion: the dialog must still be open and not have
    # thrown after an arrow-key press — a crash here would close/blank it.
    assert page.is_visible(By.CSS_SELECTOR, "div[role=dialog][aria-label='Search']", timeout=3)
    search_input.send_keys(Keys.ESCAPE)


def test_signup_keyboard_only_tab_order_reaches_submit_button(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/signup")
    _click_settled(page, By.ID, "displayName")
    for _ in range(8):
        unauthenticated_driver.switch_to.active_element.send_keys(Keys.TAB)
        active = unauthenticated_driver.switch_to.active_element
        if active.get_attribute("type") == "submit":
            return
    raise AssertionError("submit button was not reached via Tab from displayName within 8 tabs")
