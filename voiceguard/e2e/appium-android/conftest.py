"""Shared fixtures for the native Android app suite.

Sibling to ../appium (which drives the same React frontend through mobile
Chrome under UiAutomator2 — no native mobile client existed until this
Capacitor Android app). This suite instead launches the real, packaged
com.voiceguard.app APK and drives its bundled WebView, so it's the one place
that actually exercises: the native app shell launching, the Android runtime
permission dialog for microphone recording, and the hardware back button —
none of which the mobile-web suite can reach at all.

Requires a running Appium server, an Android emulator/device with the debug
APK already built (frontend/android/app/build/outputs/apk/debug/app-debug.apk,
or VOICEGUARD_APK_PATH) — see .github/workflows/android-app.yml's
appium-android-tests job for the CI setup. Not runnable on a plain dev
machine without the Android SDK, same as ../appium.
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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

THIS_DIR = Path(__file__).parent

# Reuses ../appium/pages/*.py directly — pure CSS/XPath Selenium wrappers
# (BasePage only ever calls driver.get/find_elements/execute_script) with no
# assumption baked in about the driver being a browser rather than a
# WEBVIEW context inside a packaged app. Forking a second copy of that
# already-hardened page-object code just because the session now launches an
# APK instead of mobile Chrome would be pure duplication, not a real
# difference in what needs testing.
sys.path.insert(0, str(THIS_DIR.parent / "appium"))
sys.path.insert(0, str(THIS_DIR))

from data.users import FIXTURE_USER  # noqa: E402
from pages.auth_pages import LandingPage, LoginPage  # noqa: E402

APPIUM_SERVER_URL = os.environ.get("APPIUM_SERVER_URL", "http://127.0.0.1:4723")
APP_PACKAGE = "com.voiceguard.app"
APP_ACTIVITY = ".MainActivity"
APK_PATH = os.environ.get(
    "VOICEGUARD_APK_PATH",
    str(
        THIS_DIR.parent.parent
        / "frontend"
        / "android"
        / "app"
        / "build"
        / "outputs"
        / "apk"
        / "debug"
        / "app-debug.apk"
    ),
)
# The app's own WebView origin (frontend/capacitor.config.ts's
# androidScheme: 'https'). Page objects built for ../appium navigate via
# f"{base_url}{path}" (BasePage.goto), but it's unverified whether
# Capacitor's bundled local asset server serves index.html as an SPA
# fallback for an arbitrary deep-linked path the way vercel.json's rewrite
# does for the real web deployment — so this suite drives every navigation
# after initial launch through real UI taps instead (see test_app_native.py),
# and only uses base_url for BasePage's url-based waits/assertions.
BASE_URL = "https://localhost"

RESULTS_DIR = THIS_DIR.parent / "results"
SCREENSHOTS_DIR = RESULTS_DIR / "screenshots"


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


def _switch_to_webview(drv, timeout: int = 90) -> str:
    deadline = time.time() + timeout
    seen: list[str] = []
    while time.time() < deadline:
        seen = drv.contexts
        webview_ctx = next((c for c in seen if c.startswith("WEBVIEW")), None)
        if webview_ctx:
            drv.switch_to.context(webview_ctx)
            return webview_ctx
        time.sleep(1)
    raise RuntimeError(f"No WEBVIEW context appeared within {timeout}s (contexts seen: {seen})")


@pytest.fixture(scope="session")
def driver():
    if not Path(APK_PATH).exists():
        pytest.exit(
            f"APK not found at {APK_PATH} — build it first (cd frontend && npm run build && "
            "npx cap sync android && cd android && ./gradlew assembleDebug), or point "
            "VOICEGUARD_APK_PATH at an existing debug APK.",
            returncode=1,
        )

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.app = APK_PATH
    options.app_package = APP_PACKAGE
    options.app_activity = APP_ACTIVITY
    # Fresh install + cleared app data every session — guarantees a real
    # logged-out cold start (no leftover bearer tokens in Capacitor
    # Preferences from a previous run on the same AVD), which the whole
    # fixture design below (unauthenticated landing page, then one real
    # login) depends on.
    options.full_reset = False
    options.no_reset = False
    # Deliberately NOT auto-granting permissions:
    # test_microphone_permission_and_recording_flow exercises the real OS
    # permission dialog (Phase 8), which autoGrantPermissions would skip.
    options.set_capability("autoGrantPermissions", False)
    options.new_command_timeout = 120
    options.adb_exec_timeout = 300_000
    options.uiautomator2_server_install_timeout = 300_000
    options.uiautomator2_server_launch_timeout = 300_000
    # Same real problem ../appium/conftest.py documents for mobile Chrome:
    # the api-level 33 google_apis image has no chromedriver Appium's
    # chromedriverAutodownload can resolve (it only targets the newer
    # Chrome-for-Testing endpoint). Unlike that suite, the WebView driving
    # THIS app is the Android System WebView component, not the standalone
    # Chrome browser app — the two can be on different Chromium builds even
    # on the same system image, so ../appium's pinned 109.0.5414.74 driver
    # is a starting guess here, not a confirmed match. If Appium's own error
    # names a different required version, pin CHROMEDRIVER_EXECUTABLE to
    # that instead (see android-app.yml).
    chromedriver_executable = os.environ.get("CHROMEDRIVER_EXECUTABLE")
    if chromedriver_executable:
        options.set_capability("chromedriverExecutable", chromedriver_executable)

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
    # A real device run observed the app land on the Android home screen
    # instead of staying foregrounded right after session creation (a
    # UiAutomator2/chromedriver-attach side effect, not app behavior) —
    # confirm it's actually in front before anything below assumes so.
    drv.activate_app(APP_PACKAGE)
    _switch_to_webview(drv)
    yield drv
    drv.quit()


@pytest.fixture(scope="session")
def authenticated_driver(driver, base_url):
    """Session-scoped and logs in exactly once for the whole run — same
    rate-limit reasoning as ../appium/conftest.py's identical fixture (the
    backend's login rate limit is 10/hour/IP). A fresh install (no_reset
    above) means the app is guaranteed to launch straight to the guest
    LandingPage, so there's no cookie/token state to clear first the way the
    mobile-web suite's unauthenticated_driver has to for a shared browser
    session.
    """
    landing = LandingPage(driver, base_url)
    assert landing.main_content_visible(), "App did not launch to the landing page"

    # LandingPage.tsx renders FOUR <a href="/login"> elements (Navbar's
    # desktop-only link — "hidden md:flex", so not displayed at phone width
    # — plus the hero/CTA sections' real buttons), confirmed via a real
    # device run's page source. A bare `//a[@href="/login"]` locator always
    # resolves to the first one in DOM order (Navbar's, hidden here), which
    # element_to_be_clickable correctly refuses to ever consider clickable —
    # hence a real 15s timeout rather than a quick, obvious failure. Filter
    # to the one that's actually displayed instead of guessing a more
    # specific selector that could just as easily start matching the wrong
    # element again after a future copy change.
    def _visible_login_link(drv):
        for el in drv.find_elements(By.XPATH, '//a[@href="/login"]'):
            if el.is_displayed():
                return el
        return False

    WebDriverWait(driver, 15).until(_visible_login_link).click()
    login = LoginPage(driver, base_url)
    login.login(FIXTURE_USER["email"], FIXTURE_USER["password"])
    login.wait_url_contains("/dashboard", timeout=20)
    return driver


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
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
        pass
