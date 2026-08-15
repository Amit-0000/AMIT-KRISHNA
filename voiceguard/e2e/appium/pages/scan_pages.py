"""Page objects for the scan-detection flow: /scan/new, /scan/processing,
/scan/:scanId (result), /history/:scanId (detail) — all inside AuthGuard +
OnboardingGuard + AppShell (frontend/src/App.tsx).

Selectors are taken directly from the real components:
  frontend/src/pages/NewScan/{index,components/UploadDropzone,
    components/FileCard,components/UploadActions}.tsx
  frontend/src/pages/ScanProcessing/index.tsx
  frontend/src/pages/ScanResult/{index,components/VerdictCard}.tsx
  frontend/src/pages/ScanDetail/index.tsx
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import DEFAULT_TIMEOUT, BasePage

# Injects the file directly via JS instead of input.send_keys(file_path):
# send_keys() on a real desktop Selenium node uploads local file bytes by
# path, but here the browser runs inside the Android emulator, which has no
# access to the CI runner's filesystem -- send_keys() silently "selects" the
# host path as a bare filename with zero bytes (confirmed via a real CI
# run's failure screenshot: FileCard showed "sample.wav" / "0 KB", and the
# upload failed with a real "check your connection" error since there was
# genuinely no content to send). Building a File from the real bytes and
# assigning it through a DataTransfer is the standard way to drive an
# <input type=file> when the test runner and browser don't share a
# filesystem.
_INJECT_FILE_JS = """
const [input, base64Data, filename, mimeType] = arguments;
const byteChars = atob(base64Data);
const bytes = new Uint8Array(byteChars.length);
for (let i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i);
const file = new File([bytes], filename, { type: mimeType });
const dataTransfer = new DataTransfer();
dataTransfer.items.add(file);
input.files = dataTransfer.files;
input.dispatchEvent(new Event('change', { bubbles: true }));
"""


class NewScanPage(BasePage):
    # NewScan/components/UploadDropzone.tsx: the real <input type=file> is
    # `sr-only` (visually hidden) and file-selectable via send_keys()
    # regardless — but that means it never satisfies BasePage.find()'s
    # visibility_of_element_located, so this page object queries it directly
    # via presence (driver's implicit_wait, set in conftest.py, covers the
    # retry window instead).
    FILE_INPUT = (By.CSS_SELECTOR, "input[type=file]")
    # NewScan/components/UploadActions.tsx: aria-label is static regardless
    # of error/retry state.
    ANALYZE_BUTTON = (By.CSS_SELECTOR, "button[aria-label='Analyze audio for AI detection']")
    # Same button toggles between "Remove file" (idle) and "Cancel upload"
    # (mid-upload) — match either real aria-label.
    REMOVE_OR_CANCEL_BUTTON = (
        By.XPATH,
        "//button[@aria-label='Remove file' or @aria-label='Cancel upload']",
    )
    DROPZONE = (By.CSS_SELECTOR, "[role=button][aria-label^='Upload audio file']")

    def goto_new_scan(self) -> None:
        self.goto("/scan/new")

    def upload(self, file_path: str) -> None:
        data = base64.b64encode(Path(file_path).read_bytes()).decode("ascii")
        filename = Path(file_path).name
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        input_el = self.driver.find_element(*self.FILE_INPUT)
        self.driver.execute_script(_INJECT_FILE_JS, input_el, data, filename, mime_type)

    def analyze(self) -> None:
        self.tap(self.find_clickable(*self.ANALYZE_BUTTON))

    def has_file_selected(self) -> bool:
        return self.is_visible(*self.REMOVE_OR_CANCEL_BUTTON, timeout=DEFAULT_TIMEOUT)

    def wait_navigated_to_processing(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.wait_url_contains("/scan/processing", timeout=timeout)

    def wait_upload_error(self, timeout: int = DEFAULT_TIMEOUT) -> str:
        # UploadActions.tsx renders a real role=alert with the backend's
        # rejection reason once a submit fails (e.g. duplicate-content
        # rejection — api/scans/service.py's find_active_duplicate).
        return self.alert_text(timeout=timeout)


class ScanProcessingPage(BasePage):
    def goto_processing(self, scan_id: str | None = None) -> None:
        if scan_id:
            self.goto(f"/scan/processing?id={scan_id}")
        else:
            self.goto("/scan/processing")

    def wait_redirected_to_new_scan(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        # ScanProcessing/index.tsx: no `?id=` query param -> immediate
        # navigate('/scan/new', { replace: true }).
        self.wait_url_contains("/scan/new", timeout=timeout)


class ScanResultPage(BasePage):
    VERDICT_HEADING = (By.CSS_SELECTOR, "h1")
    TECHNICAL_DETAILS_TOGGLE = (By.CSS_SELECTOR, "button[aria-expanded]")
    NOT_FOUND_TEXT = (By.XPATH, "//p[contains(text(), 'This scan could not be found')]")
    START_NEW_SCAN_LINK = (By.LINK_TEXT, "Start a new scan")
    VIEW_HISTORY_LINK = (By.LINK_TEXT, "View history")

    def goto_result(self, scan_id: str) -> None:
        self.goto(f"/scan/{scan_id}")

    def is_not_found(self, timeout: int = DEFAULT_TIMEOUT) -> bool:
        # ScanResultPage's NotReadyFallback: an unknown scanId's status
        # probe 404s -> "This scan could not be found." (real copy, index.tsx).
        return self.is_visible(*self.NOT_FOUND_TEXT, timeout=timeout)


class ScanDetailPage(BasePage):
    NOT_FOUND_TEXT = (By.XPATH, "//p[contains(text(), 'This scan could not be found')]")
    BACK_TO_HISTORY_LINK = (By.LINK_TEXT, "Back to history")

    def goto_detail(self, scan_id: str) -> None:
        self.goto(f"/history/{scan_id}")

    def is_not_found(self, timeout: int = DEFAULT_TIMEOUT) -> bool:
        # ScanDetailPage's NotFoundState: real copy for a scanId the API
        # 404s on (frontend/src/pages/ScanDetail/index.tsx).
        return self.is_visible(*self.NOT_FOUND_TEXT, timeout=timeout)
