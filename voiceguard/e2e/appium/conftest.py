"""Shared fixtures for the Appium mobile-web suite.

VoiceGuard has no native mobile client — this suite drives the same React
frontend as the Selenium suite, but through Appium's UiAutomator2 driver
controlling real mobile Chrome on an Android emulator, exercising the
responsive/mobile-viewport UI path (touch events, mobile viewport CSS,
mobile Chrome quirks) that desktop Selenium can't reach.

Requires a running Appium server (`appium --base-path /wd/hub`) with an
Android emulator/device attached — see .github/workflows/qa-suite.yml's
`appium-tests` job for the CI setup (reactivecircus/android-emulator-
runner). Not runnable on a plain dev machine without the Android SDK, so
this suite is CI-only.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Lets test modules do `from pages.base_page import BasePage` / `from data.users
# import ...` regardless of how/where pytest is invoked from, without needing
# __init__.py-based package discovery to line up with cwd.
sys.path.insert(0, str(Path(__file__).parent))

from data.users import FIXTURE_USER  # noqa: E402

APPIUM_SERVER_URL = os.environ.get("APPIUM_SERVER_URL", "http://127.0.0.1:4723")
BASE_URL = os.environ.get("APPIUM_BASE_URL", "http://10.0.2.2:5173")  # 10.0.2.2 = host machine, from the emulator

# e2e/results/, not e2e/appium/results/ — the shared output directory the CI
# workflow already points --json-report-file at for this suite (and where
# selenium_report.json already lands), so parse_results.py/build_html_report.py
# and this suite's screenshots all live next to each other.
RESULTS_DIR = Path(__file__).parent.parent / "results"
SCREENSHOTS_DIR = RESULTS_DIR / "screenshots"


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def driver():
    # Session-scoped: installing + launching the UiAutomator2 server APK is
    # the expensive part of session creation (observed 2-9 min under CI's
    # 2-vCPU runner, shared with the app's own Docker stack) — pay that cost
    # once per run, not once per test. Tests share this one browser/cookie
    # jar, so auth state must be managed deliberately (see
    # authenticated_driver/unauthenticated_driver below) rather than assumed
    # fresh: /login and /signup ARE guarded (GuestGuard, frontend/src/App.tsx)
    # and redirect away once a session cookie exists.
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.browser_name = "Chrome"
    options.set_capability("chromeOptions", {"args": ["--disable-fullscreen"]})
    options.new_command_timeout = 120
    # GitHub-hosted runners' emulator shares 2 vCPUs with the app's own
    # Docker stack, and even with a cached AVD snapshot and a single
    # session-scoped session, the UiAutomator2 instrumentation launch has
    # been observed consistently exceeding 120s there (every retry hitting
    # the same "instrumentation process cannot be initialized within
    # 120000ms" error, not the emulator itself failing to boot) — a
    # deterministic "needs more time" ceiling rather than random flakiness.
    # Give it real headroom instead of racing it.
    options.adb_exec_timeout = 300_000
    options.uiautomator2_server_install_timeout = 300_000
    options.uiautomator2_server_launch_timeout = 300_000
    # The api-level 33 google_apis emulator image ships a stock Chrome
    # (109.0.5414) with no bundled chromedriver matching it, and Appium's
    # chromedriverAutodownload only resolves against the Chrome-for-Testing
    # endpoint, which has nothing before Chrome 115 — it silently finds no
    # match and every test fails with "No Chromedriver found". The CI
    # workflow downloads the matching 109.0.5414.74 driver from the legacy
    # endpoint and points us at it directly instead.
    chromedriver_executable = os.environ.get("CHROMEDRIVER_EXECUTABLE")
    if chromedriver_executable:
        options.set_capability("chromedriverExecutable", chromedriver_executable)

    # Session creation talks to the emulator's system server (e.g. to reset
    # the hidden-api-policy setting) before the UiAutomator2 server APK is
    # even installed. On CI that server can still be settling right after
    # boot, which surfaces as a transient WebDriverException on the first
    # attempt only — retry a couple of times before failing the test.
    last_error: WebDriverException | None = None
    drv = None
    for attempt in range(3):
        try:
            drv = webdriver.Remote(APPIUM_SERVER_URL, options=options)
            break
        except WebDriverException as exc:
            last_error = exc
            time.sleep(10)
    if drv is None:
        assert last_error is not None
        raise last_error

    drv.implicitly_wait(5)
    yield drv
    drv.quit()


@pytest.fixture(scope="session")
def authenticated_driver(driver, base_url):
    # Session-scoped and logs in exactly once for the whole run, not once
    # per test. Two real constraints force this: (1) the backend's default
    # login rate limit is 10/hour/IP (see
    # performance/docker-compose.loadtest.yml's override note) — a suite
    # this size resubmitting the login form per test would blow through
    # that budget on infra grounds having nothing to do with app
    # correctness; (2) driver is a single shared browser session, so a
    # second real submission while already authenticated races GuestGuard's
    # redirect-away-from-/login (frontend/src/guards/GuestGuard.tsx) — the
    # login form may already be gone by the time find_element runs.
    # Explicit waits, not bare find_element + the driver's implicit wait:
    # confirmed live on the sibling Selenium suite that this fixture's very
    # first invocation, when it happens to run right after an
    # unauthenticated_driver test's teardown navigation (driver.get(base_url)
    # to restore cookie state), can hit a StaleElementReferenceException on
    # the email field — a race between that teardown's navigation settling
    # and this setup's own driver.get("/login") + immediate find_element,
    # not something the implicit wait reliably absorbs.
    # "css selector"/"#email", not "id"/"email": unlike plain Selenium's
    # WebDriver (which rewrites By.ID to a CSS selector before sending it
    # over the wire), Appium's AppiumLocatorConverter passes locators
    # through unchanged so native-app resource-id lookups keep working —
    # which means a raw "id" strategy reaches chromedriver as-is here, and
    # W3C-only chromedriver rejects "id" as an invalid locator strategy.
    driver.get(f"{base_url}/login")
    WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located(("css selector", "#email"))
    ).send_keys(FIXTURE_USER["email"])
    WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located(("css selector", "#password"))
    ).send_keys(FIXTURE_USER["password"])
    WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable(("css selector", "button[type=submit]"))
    ).click()
    WebDriverWait(driver, 15).until(EC.url_contains("/dashboard"))
    return driver


@pytest.fixture
def unauthenticated_driver(driver, base_url):
    """For tests that need a guest (logged-out) view of a GuestGuard-protected
    page (/signup, /login, /forgot-password, /reset-password) or that assert
    AuthGuard's redirect-to-/login behavior. Clears the shared driver's
    session cookies rather than assuming the browser starts each test
    logged out — it won't, once any test in this run has used
    authenticated_driver. Cheap (in-browser cookie clear, no new Appium
    session) unlike re-creating the driver per test.

    Restores those cookies on teardown instead of leaving the browser
    logged out — confirmed necessary by a real full-suite run: without this,
    every authenticated_driver test that happened to run after ANY
    unauthenticated_driver test in collection order silently got a
    logged-out browser (authenticated_driver's fixture body only runs once
    per session and just returns the cached driver reference — it doesn't
    re-check auth state), got redirected to /login by AuthGuard, and timed
    out waiting for content that could never appear. Restoring via saved
    cookies rather than a real re-login keeps the same rate-limit
    protection authenticated_driver exists for.

    get_cookies()/delete_all_cookies() only see cookies visible from the
    *current page's path*, and this backend deliberately scopes its
    refresh_token cookie to path=/api/v1/auth (api/auth/service.py's
    REFRESH_COOKIE_PATH) — a path the frontend SPA itself never navigates to.
    Calling those from an ordinary frontend route therefore never actually
    deleted refresh_token; it stayed live in the browser, and the frontend
    HTTP client's own 401 -> silent-refresh-via-POST-/api/v1/auth/refresh
    flow used it to transparently re-authenticate mid-test the moment any
    guest-page auth check 401'd — so a "logged out" guest test could render
    as a fully authenticated user instead (confirmed via a captured failure
    screenshot from a real CI run: /signup landed on the real Login page's
    content instead of rendering the guest form). Ported here from the
    identical, already-diagnosed-and-fixed issue in the sibling Selenium
    suite (e2e/selenium/conftest.py's unauthenticated_driver) rather than
    re-derived from scratch. _COOKIE_SCOPE_PATH below is a route that
    doesn't exist on the backend (any 404 there is fine — nothing reads the
    response) but is still same-origin and under /api/v1/auth, which makes
    refresh_token visible to the read+clear that follows while the browser
    briefly sits there.

    Only ONE extra navigation per test, at setup — not two. add_cookie() is
    NOT path-restricted the way get_cookies()/delete_all_cookies() are —
    setting a cookie for a given path works from anywhere, only *reading or
    deleting* one requires being on a matching path — so teardown restores
    directly via add_cookie() with no navigation at all (the sibling
    Selenium suite's docstring documents two rejected alternatives, each
    confirmed worse against a real CI run: a CDP-based version that avoids
    the navigation entirely but crashed the shared session outright, and a
    second navigation at teardown that avoided that crash but still
    destabilized the long-lived shared session). This also can't be
    simplified to reading+caching refresh_token once per whole run instead
    of once per test: the backend rotates refresh_token on every use and
    treats reuse of an already-rotated token as a theft signal that revokes
    every session for the user — restoring a stale cached value after any
    silent refresh happened elsewhere in the run would be actively wrong,
    not just less correct, so the current real value has to be re-read
    fresh at each test's own setup.
    """
    _COOKIE_SCOPE_PATH = "/api/v1/auth/__appium_cookie_scope__"
    driver.get(f"{base_url}{_COOKIE_SCOPE_PATH}")
    saved_cookies = driver.get_cookies()
    driver.delete_all_cookies()
    yield driver
    driver.delete_all_cookies()
    for cookie in saved_cookies:
        try:
            driver.add_cookie(cookie)
        except WebDriverException:
            # Best-effort per-cookie: one incompatible cookie attribute
            # must not stop the rest of the session from being restored.
            pass


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # Only the "call" phase (not setup/teardown) reflects an actual test
    # failure worth a screenshot — a fixture error in "setup" has no
    # meaningful page state to capture yet.
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return

    drv = item.funcargs.get("driver") or item.funcargs.get("authenticated_driver")
    if drv is None:
        return

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = item.nodeid.replace("/", "_").replace("::", "__").replace(" ", "_")
    try:
        drv.save_screenshot(str(SCREENSHOTS_DIR / f"{safe_name}.png"))
    except WebDriverException:
        # Best-effort: a screenshot failure must never mask the real test
        # failure this hook is reacting to.
        pass
