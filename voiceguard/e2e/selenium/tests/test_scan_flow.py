"""Desktop coverage of the core detection flow: upload -> processing ->
result/detail, plus the real duplicate-upload rejection feature
(api/scans/service.py's find_active_duplicate — see
performance/k6/baseline_load_test.js's uniqueWavBytes() comment for the
same constraint on the load-test side).

Tests within this file rely on declaration order (pytest's default) for the
upload -> duplicate-reject -> result/detail/history sequence: only ONE real
upload happens in this whole suite (test_upload_valid_audio_file_...), and
downstream tests read its outcome back out of the shared browser/`_state`
rather than re-uploading, since a second identical upload is a rejection by
design. This is a separate CI job/backend instance from the Appium suite's
own single real upload, so no cross-suite interference.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.history_page import HistoryPage
from pages.scan_pages import NewScanPage, ScanDetailPage, ScanProcessingPage, ScanResultPage

pytestmark = [pytest.mark.high]

SAMPLE_WAV = str(Path(__file__).resolve().parents[3] / "performance" / "k6" / "sample.wav")
SAMPLE_WAV_FILENAME = Path(SAMPLE_WAV).name

# Populated by test_upload_valid_audio_file_shows_file_card_and_starts_analysis,
# read by the tests that follow it in this file.
_state: dict = {}


def test_new_scan_page_shows_upload_dropzone(authenticated_driver, base_url):
    page = NewScanPage(authenticated_driver, base_url)
    page.goto_new_scan()
    assert page.is_visible(*page.DROPZONE)
    assert page.driver.find_elements(*page.FILE_INPUT), "no <input type=file> present on /scan/new"


def test_scan_processing_without_id_redirects_to_new_scan(authenticated_driver, base_url):
    page = ScanProcessingPage(authenticated_driver, base_url)
    page.goto_processing()
    page.wait_redirected_to_new_scan()


def test_scan_result_unknown_id_shows_not_found(authenticated_driver, base_url):
    page = ScanResultPage(authenticated_driver, base_url)
    page.goto_result(str(uuid.uuid4()))
    assert page.is_not_found()


def test_scan_detail_unknown_id_shows_not_found(authenticated_driver, base_url):
    page = ScanDetailPage(authenticated_driver, base_url)
    page.goto_detail(str(uuid.uuid4()))
    assert page.is_not_found()
    assert page.is_visible(*page.BACK_TO_HISTORY_LINK)


def test_upload_valid_audio_file_shows_file_card_and_starts_analysis(authenticated_driver, base_url):
    page = NewScanPage(authenticated_driver, base_url)
    page.goto_new_scan()
    page.upload(SAMPLE_WAV)
    assert page.has_file_selected(), "FileCard's Remove/Cancel control never appeared after upload"
    page.analyze()
    page.wait_navigated_to_processing()

    scan_id = authenticated_driver.current_url.split("id=")[-1]
    assert scan_id, f"no ?id= query param on {authenticated_driver.current_url}"
    _state["scan_id"] = scan_id
    _state["filename"] = SAMPLE_WAV_FILENAME


def test_uploading_duplicate_active_scan_is_rejected(authenticated_driver, base_url):
    assert _state.get("scan_id"), "must run after test_upload_valid_audio_file_..."
    page = NewScanPage(authenticated_driver, base_url)
    page.goto_new_scan()
    page.upload(SAMPLE_WAV)
    page.analyze()
    reason = page.wait_upload_error()
    assert reason, "expected a real role=alert rejection reason for the duplicate upload"


def test_uploaded_scan_appears_in_history(authenticated_driver, base_url):
    assert _state.get("filename"), "must run after test_upload_valid_audio_file_..."
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    assert page.is_showing_table(), "history should show the real scan table once at least one scan exists"
    row = page.row_for_filename(_state["filename"])
    assert row is not None


def test_uploaded_scan_result_page_reaches_a_real_state(authenticated_driver, base_url):
    assert _state.get("scan_id"), "must run after test_upload_valid_audio_file_..."
    page = ScanResultPage(authenticated_driver, base_url)
    page.goto_result(_state["scan_id"])
    # Inference timing/availability isn't something this suite controls
    # (CPU-bound model, see project memory on LCNN CPU inference) — accept
    # either real terminal outcome: a rendered verdict, or the page routing
    # back to /scan/processing because it isn't complete yet.
    WebDriverWait(authenticated_driver, 20).until(
        lambda d: "/scan/processing" in d.current_url or page.is_visible(*page.VERDICT_HEADING, timeout=1)
    )


def test_uploaded_scan_detail_page_reaches_a_real_state(authenticated_driver, base_url):
    assert _state.get("scan_id"), "must run after test_upload_valid_audio_file_..."
    page = ScanDetailPage(authenticated_driver, base_url)
    page.goto_detail(_state["scan_id"])
    assert not page.is_not_found(timeout=5), "a scan we just uploaded must not show the not-found state"


def test_new_scan_page_reachable_directly_via_url(authenticated_driver, base_url):
    page = NewScanPage(authenticated_driver, base_url)
    page.goto_new_scan()
    assert "/scan/new" in page.current_url
    assert "/login" not in page.current_url


def test_new_scan_analyze_button_absent_before_file_selected(authenticated_driver, base_url):
    # NewScan/index.tsx: UploadActions (which owns the Analyze button) only
    # renders once state.file !== null -- confirmed real behavior, not
    # assumed, by reading the component's showFileCard condition.
    page = NewScanPage(authenticated_driver, base_url)
    page.goto_new_scan()
    assert not page.driver.find_elements(*page.ANALYZE_BUTTON), "Analyze button should not exist before a file is chosen"


def test_new_scan_remove_or_cancel_control_absent_before_file_selected(authenticated_driver, base_url):
    page = NewScanPage(authenticated_driver, base_url)
    page.goto_new_scan()
    assert not page.has_file_selected(), "no file has been chosen yet on a fresh /scan/new load"


def test_scan_processing_with_id_stays_on_processing_page(authenticated_driver, base_url):
    assert _state.get("scan_id"), "must run after test_upload_valid_audio_file_..."
    page = ScanProcessingPage(authenticated_driver, base_url)
    page.goto_processing(_state["scan_id"])
    assert "/scan/processing" in page.current_url
    assert f"id={_state['scan_id']}" in page.current_url


def test_scan_result_page_has_start_new_scan_link_when_not_found(authenticated_driver, base_url):
    page = ScanResultPage(authenticated_driver, base_url)
    page.goto_result(str(uuid.uuid4()))
    assert page.is_not_found()
    assert page.is_visible(*page.START_NEW_SCAN_LINK)


def test_scan_result_not_found_state_has_no_view_history_link(authenticated_driver, base_url):
    # ScanResult/index.tsx's NotReadyFallback (the real not-found component)
    # only renders "Start a new scan" -- VIEW_HISTORY_LINK belongs to the
    # separate success/verdict-shown branch, unreachable for a scan that
    # doesn't exist. Confirmed by reading the component, not assumed.
    page = ScanResultPage(authenticated_driver, base_url)
    page.goto_result(str(uuid.uuid4()))
    assert page.is_not_found()
    assert not page.is_visible(*page.VIEW_HISTORY_LINK, timeout=2)


def test_scan_result_start_new_scan_link_navigates(authenticated_driver, base_url):
    page = ScanResultPage(authenticated_driver, base_url)
    page.goto_result(str(uuid.uuid4()))
    page.is_not_found()
    page.click(page.find_clickable(*page.START_NEW_SCAN_LINK))
    page.wait_url_contains("/scan/new")
    assert "/scan/new" in page.current_url


def test_scan_detail_back_to_history_link_navigates(authenticated_driver, base_url):
    page = ScanDetailPage(authenticated_driver, base_url)
    page.goto_detail(str(uuid.uuid4()))
    page.is_not_found()
    page.click(page.find_clickable(*page.BACK_TO_HISTORY_LINK))
    page.wait_url_contains("/history")
    assert "/history" in page.current_url


def test_new_scan_rejects_non_audio_file_client_side(authenticated_driver, base_url, tmp_path):
    # Client-side extension/type validation (NewScan/components/
    # UploadValidation.tsx, role=alert) -- a plain .txt file must never
    # reach the backend at all, so this doesn't touch the one-real-upload
    # budget this file's module docstring documents.
    bad_file = tmp_path / "not-audio.txt"
    bad_file.write_text("this is not an audio file")
    page = NewScanPage(authenticated_driver, base_url)
    page.goto_new_scan()
    page.upload(str(bad_file))
    assert page.is_visible("css selector", "[role=alert]", timeout=10)


def test_duplicate_upload_rejection_can_be_triggered_more_than_once(authenticated_driver, base_url):
    # Real, deterministic content-hash-based rejection (api/scans/service.py
    # find_active_duplicate) -- reusable indefinitely for the same file,
    # unlike a real analysis run, so a second confirmation is a real,
    # independent assertion, not a flaky repeat of the same test.
    assert _state.get("scan_id"), "must run after test_upload_valid_audio_file_..."
    page = NewScanPage(authenticated_driver, base_url)
    page.goto_new_scan()
    page.upload(SAMPLE_WAV)
    page.analyze()
    reason = page.wait_upload_error()
    assert reason
