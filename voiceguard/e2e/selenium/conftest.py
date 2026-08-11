"""Shared fixtures for the desktop Selenium web E2E suite.

Runs headless Chrome against the frontend dev server (docker-compose's
`frontend` service, http://localhost:5173 by default) and reuses the DAST
fixture accounts (automated_test/setup_env.py) for the authenticated flows,
so this suite doesn't need its own signup/verify bootstrapping.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Lets test modules do `from pages.base_page import BasePage` / `from data.users
# import ...` regardless of how/where pytest is invoked from — same reasoning
# as voiceguard/e2e/appium/conftest.py's identical line.
sys.path.insert(0, str(Path(__file__).parent))

from data.users import FIXTURE_USER  # noqa: E402

BASE_URL = os.environ.get("SELENIUM_BASE_URL", "http://localhost:5173")
REPO_ROOT = Path(__file__).resolve().parents[3]
INPUT_JSON = REPO_ROOT / "automated_test" / "input.json"

# e2e/results/, shared with the Appium suite's identical output directory
# (and where selenium_report.json already lands) — parse_results.py/
# build_html_report.py/build_excel.py and this suite's screenshots all live
# next to each other, same convention as e2e/appium/conftest.py.
RESULTS_DIR = Path(__file__).parent.parent / "results"
SCREENSHOTS_DIR = RESULTS_DIR / "screenshots"


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def driver():
    # Session-scoped: a plain headless Chrome launch is cheap (unlike
    # Appium's UiAutomator2 session), but authenticated_driver below still
    # needs one shared browser to log in on *once* rather than once per
    # test — see its docstring for why. Reusing one driver for the whole
    # run also avoids ~120 separate Chrome process launches.
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(2)
    yield drv
    drv.quit()


@pytest.fixture(scope="session")
def authenticated_driver(driver, base_url):
    # Session-scoped and logs in exactly once for the whole run, not once
    # per test — same two real constraints as Appium's identical fixture:
    # (1) the backend's default login rate limit is 10/hour/IP (see
    # performance/docker-compose.loadtest.yml's override note) — a suite
    # this size resubmitting the login form per test would blow through
    # that budget on infra grounds having nothing to do with app
    # correctness; (2) driver is a single shared browser session, so a
    # second real submission while already authenticated races GuestGuard's
    # redirect-away-from-/login (frontend/src/guards/GuestGuard.tsx).
    # Explicit waits, not bare find_element + the driver's 2s implicit
    # wait: confirmed live that this fixture's very first invocation, when
    # it happens to run right after an unauthenticated_driver test's
    # teardown navigation (driver.get(base_url) to restore cookie state),
    # can hit a StaleElementReferenceException on the email field — a race
    # between that teardown's navigation settling and this setup's own
    # driver.get("/login") + immediate find_element, not something the
    # implicit wait reliably absorbs.
    driver.get(f"{base_url}/login")
    WebDriverWait(driver, 15).until(EC.visibility_of_element_located(("id", "email"))).send_keys(
        FIXTURE_USER["email"]
    )
    WebDriverWait(driver, 15).until(EC.visibility_of_element_located(("id", "password"))).send_keys(
        FIXTURE_USER["password"]
    )
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
    authenticated_driver.

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
    """
    saved_cookies = driver.get_cookies()
    driver.delete_all_cookies()
    yield driver
    # No driver.get() before restoring: the whole app is single-origin, so
    # add_cookie() works from wherever the test left the browser without an
    # extra navigation first. That extra navigation used to be here
    # defensively and turned out to be exactly what caused real, confirmed
    # ElementNotInteractable/StaleElement/Timeout failures in whichever
    # authenticated_driver-using test ran right after it — two full-page
    # navigations landing back to back (this teardown's, then the next
    # fixture's own driver.get()) raced each other in headless Chrome.
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
        # "selenium_" prefix keeps filenames distinct from the Appium
        # suite's screenshots in the same shared results/screenshots/ dir,
        # even though CI uploads them as separate artifacts anyway.
        drv.save_screenshot(str(SCREENSHOTS_DIR / f"selenium_{safe_name}.png"))
    except WebDriverException:
        # Best-effort: a screenshot failure must never mask the real test
        # failure this hook is reacting to.
        pass
