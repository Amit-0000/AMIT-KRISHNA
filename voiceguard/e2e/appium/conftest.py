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
import time

import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.common.exceptions import WebDriverException

APPIUM_SERVER_URL = os.environ.get("APPIUM_SERVER_URL", "http://127.0.0.1:4723")
BASE_URL = os.environ.get("APPIUM_BASE_URL", "http://10.0.2.2:5173")  # 10.0.2.2 = host machine, from the emulator


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def driver():
    # Session-scoped: installing + launching the UiAutomator2 server APK is
    # the expensive part of session creation (observed 2-9 min under CI's
    # 2-vCPU runner, shared with the app's own Docker stack), and neither
    # test here mutates state the others depend on (navigation resets the
    # page; /login has no auth-redirect guard, so re-visiting it while
    # already logged in is safe) — so pay that cost once per run, not once
    # per test.
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


@pytest.fixture
def authenticated_driver(driver, base_url):
    driver.get(f"{base_url}/login")
    driver.find_element("id", "email").send_keys("dast.usera@example.com")
    driver.find_element("id", "password").send_keys("DastTest!2026a")
    driver.find_element("css selector", "button[type=submit]").click()
    return driver
