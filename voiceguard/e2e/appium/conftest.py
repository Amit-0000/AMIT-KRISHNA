"""Shared fixtures for the Appium mobile-web suite.

VoiceGuard has no native mobile client — this suite drives the same React
frontend as the Selenium suite, but through Appium's UiAutomator2 driver
controlling real mobile Chrome on an Android emulator, exercising the
responsive/mobile-viewport UI path (touch events, mobile viewport CSS,
mobile Chrome quirks) that desktop Selenium can't reach.

Requires a running Appium server (`appium --base-path /wd/hub`) with an
Android emulator/device attached — see .github/workflows/qa-suite.yml's
`appium-mobile-web` job for the CI setup (reactivecircus/android-emulator-
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


@pytest.fixture
def driver():
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.browser_name = "Chrome"
    options.set_capability("chromeOptions", {"args": ["--disable-fullscreen"]})
    options.new_command_timeout = 120
    # GitHub-hosted runners' emulator is a cold KVM instance with no APK/
    # instrumentation cache, and the default timeouts here (20s/20s/30s) were
    # observed timing out installing/launching the UiAutomator2 server on it
    # (adb install + instrumentation bring-up routinely take longer than that
    # under CI resource contention, even though the emulator itself had
    # already finished booting). Give it real headroom instead of racing it.
    options.adb_exec_timeout = 120_000
    options.uiautomator2_server_install_timeout = 120_000
    options.uiautomator2_server_launch_timeout = 120_000
    # The api-level 33 google_apis emulator image ships a stock Chrome
    # (109.0.5414) with no bundled chromedriver matching it — Appium's own
    # error names this exact capability as the workaround.
    options.set_capability("chromedriverAutodownload", True)

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
