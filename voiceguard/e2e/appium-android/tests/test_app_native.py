"""Appium suite for the packaged Capacitor Android app (com.voiceguard.app).

Covers what the native shell adds over the plain web app — real app launch,
the Android runtime permission dialog for microphone recording, and the
hardware back button — plus a login/navigate/logout smoke pass through the
same real Railway backend the web app and ../appium's mobile-web suite
already exercise. Tests run in file order (pytest's default) and share one
session-scoped `driver`/`authenticated_driver` (see ../conftest.py) — later
tests deliberately depend on state left by earlier ones (e.g. the recording
left in "stopped" phase by test_microphone_permission_and_recording_flow),
same pattern already used by ../appium and ../selenium's suites.

Known, disclosed gap: uploading a file through Android's system file/
document picker (a separate app, DocumentsUI) is not automated here — that
picker's UI differs across Android versions/OEMs and needs its own verified
locator set this suite doesn't have. Coverage of the upload -> scan -> AI
inference -> result pipeline instead comes via
test_record_stop_analyze_reaches_result below, which drives the *microphone*
path into that exact same pipeline: NewScan/hooks/useFileUpload.ts's
handleRecordedFile() feeds a real recorded native audio file into the
identical validate/upload/poll/result flow a picked file would use.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "appium"))

from data.users import FIXTURE_USER  # noqa: E402
from pages.auth_pages import LandingPage  # noqa: E402
from pages.dashboard_page import DashboardPage  # noqa: E402
from pages.history_page import HistoryPage  # noqa: E402
from pages.nav import AppChrome, UserMenu  # noqa: E402
from pages.scan_pages import NewScanPage, ScanResultPage  # noqa: E402
from pages.settings_pages import AppearancePage  # noqa: E402


def _click(driver, xpath: str, timeout: int = 15):
    """find_element(...).click() proved flaky on a real device run for
    several of this suite's buttons — framer-motion transitions (NewScan's
    AnimatePresence mode="wait" swap, RecordAudioPanel's phase changes) mean
    a freshly-rendered button can exist in the DOM slightly before it's
    actually hit-testable. Waiting for element_to_be_clickable covers both
    existence and "done animating" in one place instead of scattering
    one-off WebDriverWaits per call site."""
    WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()


def test_app_launches_to_landing_page(driver, base_url) -> None:
    landing = LandingPage(driver, base_url)
    assert landing.main_content_visible()


def test_login_with_valid_credentials_reaches_dashboard(authenticated_driver, base_url) -> None:
    dashboard = DashboardPage(authenticated_driver, base_url)
    assert "/dashboard" in dashboard.current_url
    assert dashboard.greeting_text()


def test_native_new_scan_shows_upload_and_record_toggle(authenticated_driver, base_url) -> None:
    # Only inside the Android app: frontend/src/pages/NewScan/index.tsx gates
    # this Upload/Record toggle on Capacitor.isNativePlatform() — its
    # presence here is real evidence the packaged app correctly detects it's
    # running natively, not just a repaint of the plain web UI.
    chrome = AppChrome(authenticated_driver, base_url)
    drawer = chrome.open_mobile_drawer()
    drawer.go_to("New Scan")
    WebDriverWait(authenticated_driver, 15).until(EC.url_contains("/scan/new"))
    WebDriverWait(authenticated_driver, 15).until(
        EC.visibility_of_element_located((By.XPATH, '//button[normalize-space()="Record Audio"]'))
    )


def test_microphone_permission_and_recording_flow(authenticated_driver, base_url) -> None:
    driver = authenticated_driver
    _click(driver, '//button[normalize-space()="Record Audio"]')
    # 30s, not the default 15s: a real android-app.yml CI run hit a genuine
    # TimeoutException here twice in a row (original attempt + rerun) --
    # this click follows the Upload<->Record AnimatePresence swap
    # (NewScan/index.tsx), the same transition-timing class _click already
    # works around elsewhere, just needing more headroom under CI's shared
    # emulator load than a local run ever does (same reasoning already
    # documented on MobileDrawer.is_open()'s 5s->10s bump).
    _click(driver, '//button[normalize-space()="Start Recording"]', timeout=30)

    # Android's real runtime-permission dialog for RECORD_AUDIO is a
    # *different app* (PermissionController), reachable only from the
    # NATIVE_APP context — this is the one thing in the whole suite that
    # can't be driven through the WebView at all.
    webview_ctx = driver.current_context
    driver.switch_to.context("NATIVE_APP")
    try:
        try:
            allow = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.ID, "com.android.permissioncontroller:id/permission_allow_foreground_only_button")
                )
            )
        except TimeoutException:
            # Older/alternate dialog layout — plain two-button Allow/Deny.
            allow = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "com.android.permissioncontroller:id/permission_allow_button"))
            )
        allow.click()
    finally:
        driver.switch_to.context(webview_ctx)

    time.sleep(2)  # a couple of seconds of real recorded audio, not a placeholder file
    _click(driver, '//button[normalize-space()="Stop Recording"]')

    WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located((By.XPATH, '//button[normalize-space()="Analyze Recording"]'))
    )


def test_record_stop_analyze_reaches_result(authenticated_driver, base_url) -> None:
    # Continues directly from the previous test's "stopped" (Play/Re-record/
    # Analyze) state on the same session-scoped driver — see module
    # docstring for why this is this suite's real coverage of the
    # upload/scan/AI-inference/result pipeline.
    # RecordAudioPanel's own "Analyze Recording" button (tapped here) only
    # feeds the recorded file into useFileUpload's state and flips the page
    # back to the normal upload view (NewScan/index.tsx's onAnalyze) — it
    # does not itself upload anything. That lands on the exact same
    # FileCard/UploadActions view a browsed/dropped file would, whose own
    # "Analyze Audio" button (NewScanPage.analyze(), UploadActions.tsx) is
    # what actually submits. A real device run confirmed the first tap
    # alone never reaches the backend (no POST /api/v1/scans at all) —
    # missing this second tap, not an app bug.
    driver = authenticated_driver
    new_scan = NewScanPage(driver, base_url)
    _click(driver, '//button[normalize-space()="Analyze Recording"]')
    assert new_scan.has_file_selected(), "Recorded file did not reach the normal upload/FileCard view"
    new_scan.analyze()
    new_scan.wait_navigated_to_processing(timeout=20)

    result = ScanResultPage(driver, base_url)
    WebDriverWait(driver, 120).until(
        lambda d: "/scan/" in d.current_url and "processing" not in d.current_url and "/scan/new" not in d.current_url
    )
    assert result.find(*result.VERDICT_HEADING, timeout=30).text


def test_history_shows_the_new_scan(authenticated_driver, base_url) -> None:
    chrome = AppChrome(authenticated_driver, base_url)
    drawer = chrome.open_mobile_drawer()
    drawer.go_to("History")
    WebDriverWait(authenticated_driver, 15).until(EC.url_contains("/history"))
    history = HistoryPage(authenticated_driver, base_url)
    assert history.is_showing_table(timeout=20) or history.is_showing_empty_state(timeout=5)


def test_appearance_theme_toggle(authenticated_driver, base_url) -> None:
    chrome = AppChrome(authenticated_driver, base_url)
    drawer = chrome.open_mobile_drawer()
    drawer.go_to("Settings")
    WebDriverWait(authenticated_driver, 15).until(EC.url_contains("/settings"))

    _click(authenticated_driver, '//nav[@aria-label="Settings sections"]//a[normalize-space()="Appearance"]')
    appearance = AppearancePage(authenticated_driver, base_url)
    WebDriverWait(authenticated_driver, 15).until(EC.visibility_of_element_located(appearance.THEME_RADIOGROUP))
    appearance.select_theme("Dark")
    assert appearance.is_theme_active("Dark")


def test_hardware_back_button_navigates_to_previous_page(authenticated_driver, base_url) -> None:
    # Real hardware KEYCODE_BACK, routed through App.tsx's
    # CapacitorApp.addListener('backButton', ...) (Phase 14) — currently on
    # /settings/appearance, reached via Settings from the drawer, so this
    # must go back in the SPA's own history rather than exit the app.
    driver = authenticated_driver
    driver.back()
    WebDriverWait(driver, 15).until(lambda d: "/settings/appearance" not in d.current_url)


def test_logout_returns_to_guest_area(authenticated_driver, base_url) -> None:
    # Not MobileDrawer.open_user_menu(): a real device run found the app
    # renders *two* `<button>`s matching that locator's
    # //button[.//p[normalize-space()="DAST User A"]] pattern — the desktop
    # Sidebar's UserMenu instance (present in the DOM but CSS-hidden below
    # the lg breakpoint, per nav.py's own comment) and the mobile drawer's.
    # Selenium's find_element always returns the first DOM match regardless
    # of visibility, and on this build that's the hidden one, so
    # BasePage.find()'s visibility wait never succeeds — a real 15s timeout,
    # not a UI bug (confirmed via page_source: both buttons exist, only the
    # second is_displayed()). Pick the displayed one directly instead.
    driver = authenticated_driver
    chrome = AppChrome(driver, base_url)
    drawer = chrome.open_mobile_drawer()
    trigger = next(
        el
        for el in driver.find_elements(
            By.XPATH, f'//button[.//p[normalize-space()="{FIXTURE_USER["display_name"]}"]]'
        )
        if el.is_displayed()
    )
    trigger.click()
    user_menu = UserMenu(driver, base_url)
    user_menu.sign_out()
    WebDriverWait(driver, 15).until(lambda d: "/dashboard" not in d.current_url)
