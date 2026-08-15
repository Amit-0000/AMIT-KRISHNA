"""Desktop-only responsive-breakpoint coverage — genuinely new relative to
the Appium suite, which runs a fixed mobile emulator viewport and can't
resize. This suite CAN, via driver.set_window_size(), so it verifies real
breakpoint behavior instead of guessing.

Breakpoint values verified against frontend/tailwind.config.ts (no `screens`
override present, so Tailwind's defaults are in effect: sm=640, md=768,
lg=1024) and against the actual responsive classes already committed in
frontend/src/components/layout/{Sidebar,TopBar,Breadcrumb}.tsx:
  - Sidebar.tsx: `hidden lg:flex` -> visible only at >=1024px
  - TopBar.tsx hamburger button: `lg:hidden` -> visible only below 1024px
  - TopBar.tsx desktop search trigger (aria-label="Search (Command K)"):
    `hidden sm:flex` -> visible only at >=640px
  - TopBar.tsx mobile search icon (aria-label="Search"): `sm:hidden` ->
    visible only below 640px
  - Breadcrumb: `hidden sm:flex` -> visible only at >=640px
"""
from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage

pytestmark = [pytest.mark.medium]

NARROW = (375, 800)   # below every breakpoint used in this app
SM = (700, 800)        # >=640 (sm), <768 (md)
MD = (800, 800)        # >=768 (md), <1024 (lg)
LG = (1100, 800)       # >=1024 (lg)


def _no_horizontal_overflow(driver) -> bool:
    return bool(
        driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth + 1;")
    )


def test_sidebar_visible_at_lg_breakpoint(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*LG)
    page.goto("/dashboard")
    assert page.is_visible(By.CSS_SELECTOR, "nav[aria-label='Sidebar navigation']", timeout=5)


def test_sidebar_hidden_below_lg_breakpoint(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*NARROW)
    page.goto("/dashboard")
    sidebar_nav = page.driver.find_elements(By.CSS_SELECTOR, "nav[aria-label='Sidebar navigation']")
    assert sidebar_nav and not sidebar_nav[0].is_displayed(), "Sidebar's `hidden lg:flex` should hide it below 1024px"
    page.resize_window(*LG)  # leave the shared window at a known size for tests that follow


def test_mobile_hamburger_visible_below_lg_breakpoint(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*NARROW)
    page.goto("/dashboard")
    assert page.is_visible(By.CSS_SELECTOR, "button[aria-label='Open navigation']", timeout=5)
    page.resize_window(*LG)


def test_mobile_hamburger_hidden_at_lg_breakpoint(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*LG)
    page.goto("/dashboard")
    hamburgers = page.driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Open navigation']")
    assert hamburgers and not hamburgers[0].is_displayed(), "TopBar's `lg:hidden` should hide the hamburger at >=1024px"


def test_desktop_search_trigger_visible_at_sm_breakpoint(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*SM)
    page.goto("/dashboard")
    assert page.is_visible(By.CSS_SELECTOR, "button[aria-label='Search (Command K)']", timeout=5)
    page.resize_window(*LG)


def test_mobile_search_icon_visible_below_sm_breakpoint(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*NARROW)
    page.goto("/dashboard")
    assert page.is_visible(By.CSS_SELECTOR, "button[aria-label='Search']", timeout=5)
    page.resize_window(*LG)


def test_landing_page_no_horizontal_overflow_at_narrow_width(driver, base_url):
    page = BasePage(driver, base_url)
    page.resize_window(*NARROW)
    page.goto("/")
    assert _no_horizontal_overflow(page.driver)
    page.resize_window(*LG)


def test_dashboard_no_horizontal_overflow_at_narrow_width(authenticated_driver, base_url):
    # goto_dashboard(), not a bare goto("/dashboard"): a real CI run showed
    # this genuinely racing the dashboard's async data fetch (recent scans,
    # quick actions) — content still shifting the layout when scrollWidth
    # was measured immediately after the hard-reload navigation returned.
    # goto_dashboard() already waits for GREETING_HEADING (see its own
    # docstring for why a URL-only wait isn't enough), which is exactly the
    # "page is actually settled" signal this check needs too.
    page = DashboardPage(authenticated_driver, base_url)
    page.resize_window(*NARROW)
    page.goto_dashboard()
    assert _no_horizontal_overflow(page.driver)
    page.resize_window(*LG)  # leave the shared window at its normal size


AUTHENTICATED_ROUTES_FOR_OVERFLOW_CHECK = [
    "/history",
    "/notifications",
    "/help",
    "/feedback",
    "/scan/new",
    "/settings/profile",
    "/settings/account",
    "/settings/appearance",
]


@pytest.mark.parametrize("route", AUTHENTICATED_ROUTES_FOR_OVERFLOW_CHECK)
def test_no_horizontal_overflow_at_narrow_width(authenticated_driver, base_url, route):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*NARROW)
    page.goto(route)
    assert _no_horizontal_overflow(page.driver), f"{route} overflows horizontally at {NARROW[0]}px"
    page.resize_window(*LG)


GUEST_ROUTES_FOR_OVERFLOW_CHECK = ["/login", "/signup", "/forgot-password"]


@pytest.mark.parametrize("route", GUEST_ROUTES_FOR_OVERFLOW_CHECK)
def test_guest_route_no_horizontal_overflow_at_narrow_width(unauthenticated_driver, base_url, route):
    page = BasePage(unauthenticated_driver, base_url)
    page.resize_window(*NARROW)
    page.goto(route)
    assert _no_horizontal_overflow(page.driver), f"{route} overflows horizontally at {NARROW[0]}px"
    page.resize_window(*LG)


def test_breadcrumb_hidden_below_sm_breakpoint(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*NARROW)
    page.goto("/dashboard")
    crumbs = page.driver.find_elements(By.CSS_SELECTOR, 'nav[aria-label="Breadcrumb"]')
    assert crumbs and not crumbs[0].is_displayed(), "Breadcrumb's `hidden sm:flex` should hide it below 640px"
    page.resize_window(*LG)


def test_breadcrumb_visible_at_sm_breakpoint(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*SM)
    page.goto("/dashboard")
    assert page.is_visible(By.CSS_SELECTOR, 'nav[aria-label="Breadcrumb"]', timeout=5)
    page.resize_window(*LG)


def test_history_no_horizontal_overflow_at_sm_breakpoint(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*SM)
    page.goto("/history")
    assert _no_horizontal_overflow(page.driver)
    page.resize_window(*LG)


def test_sidebar_still_hidden_at_md_breakpoint(authenticated_driver, base_url):
    # Sidebar's `hidden lg:flex` triggers only at >=1024px -- 800px (md,
    # between sm and lg) is still below that threshold.
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*MD)
    page.goto("/dashboard")
    sidebar_nav = page.driver.find_elements(By.CSS_SELECTOR, "nav[aria-label='Sidebar navigation']")
    assert sidebar_nav and not sidebar_nav[0].is_displayed()
    page.resize_window(*LG)


def test_hamburger_still_visible_at_md_breakpoint(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*MD)
    page.goto("/dashboard")
    assert page.is_visible(By.CSS_SELECTOR, "button[aria-label='Open navigation']", timeout=5)
    page.resize_window(*LG)


def test_desktop_search_trigger_visible_at_md_breakpoint(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*MD)
    page.goto("/dashboard")
    assert page.is_visible(By.CSS_SELECTOR, "button[aria-label='Search (Command K)']", timeout=5)
    page.resize_window(*LG)


def test_breadcrumb_visible_at_md_breakpoint(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*MD)
    page.goto("/dashboard")
    assert page.is_visible(By.CSS_SELECTOR, 'nav[aria-label="Breadcrumb"]', timeout=5)
    page.resize_window(*LG)


def test_settings_no_horizontal_overflow_at_narrow_width(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*NARROW)
    page.goto("/settings/appearance")
    assert _no_horizontal_overflow(page.driver)
    page.resize_window(*LG)


def test_notifications_no_horizontal_overflow_at_md_breakpoint(authenticated_driver, base_url):
    page = BasePage(authenticated_driver, base_url)
    page.resize_window(*MD)
    page.goto("/notifications")
    assert _no_horizontal_overflow(page.driver)
    page.resize_window(*LG)
