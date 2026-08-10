"""Mobile-viewport-specific checks that desktop Selenium coverage can't
meaningfully assert (frontend/index.html for the viewport meta tag,
UploadDropzone's committed min-h-[340px] for a real touch-target size)."""
from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from pages.scan_pages import NewScanPage


def _has_no_horizontal_overflow(driver) -> bool:
    return bool(
        driver.execute_script(
            "return document.documentElement.scrollWidth <= window.innerWidth + 1;"
        )
    )


def test_viewport_meta_tag_present_and_mobile_scaled(driver, base_url):
    page = BasePage(driver, base_url)
    page.goto("/")
    content = page.find(By.CSS_SELECTOR, "meta[name=viewport]").get_attribute("content")
    assert "width=device-width" in content


def test_landing_page_has_no_horizontal_overflow(driver, base_url):
    page = BasePage(driver, base_url)
    page.goto("/")
    assert _has_no_horizontal_overflow(page.driver)


def test_login_page_has_no_horizontal_overflow(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/login")
    assert _has_no_horizontal_overflow(page.driver)


def test_dashboard_has_no_horizontal_overflow(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.goto("/dashboard")
    assert _has_no_horizontal_overflow(page.driver)


def test_new_scan_dropzone_meets_committed_touch_target_size(authenticated_driver, base_url):
    # NewScan/components/UploadDropzone.tsx sets a real, committed
    # `min-h-[340px]` on the dropzone — a small tolerance below that
    # accounts for DPR/zoom rounding, not an invented threshold.
    page = NewScanPage(authenticated_driver, base_url)
    page.goto_new_scan()
    dropzone = page.find(*page.DROPZONE)
    assert dropzone.size["height"] >= 300
