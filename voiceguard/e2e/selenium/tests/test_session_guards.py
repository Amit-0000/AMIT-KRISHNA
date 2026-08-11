"""Desktop coverage of the two route guards that redirect
(frontend/src/guards/AuthGuard.tsx, GuestGuard.tsx):
  - AuthGuard: unauthenticated visitor to a protected route -> /login
  - GuestGuard: authenticated visitor to a guest-only route -> /dashboard

Absorbs the old test_authenticated_flows.py's
test_unauthenticated_user_redirected_from_dashboard (the /dashboard case
below is that same assertion, now parametrized across every AuthGuard
route).

OnboardingGuard (frontend/src/guards/OnboardingGuard.tsx) is NOT covered
here: exercising its real redirect needs an authenticated session for a user
whose onboarding_completed is still false, which requires a freshly
registered *and verified* account — verification needs a real token, out of
reach for this suite for the same reason noted in
test_password_recovery.py (reserved for the DAST suite's docker-logs
mechanism). Not faked here.
"""
from __future__ import annotations

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from data.users import SECOND_FIXTURE_USER
from pages.base_page import BasePage
from pages.nav import Sidebar

pytestmark = [pytest.mark.critical]

AUTH_GUARDED_ROUTES = [
    "/dashboard",
    "/history",
    "/settings/profile",
    "/feedback",
    "/scan/new",
    "/scan/processing",
    "/notifications",
    "/help",
    "/settings/account",
    "/settings/appearance",
]
GUEST_GUARDED_ROUTES = ["/login", "/signup", "/forgot-password", "/reset-password"]

# Real, fully public routes — neither AuthGuard nor GuestGuard wraps these
# (frontend/src/App.tsx), so an unauthenticated visitor must reach them
# directly without any redirect at all.
UNGUARDED_ROUTES = ["/", "/verify-email"]


@pytest.mark.parametrize("route", AUTH_GUARDED_ROUTES)
def test_authguard_redirects_unauthenticated_user_to_login(unauthenticated_driver, base_url, route):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto(route)
    page.wait_url_contains("/login")
    assert "/login" in page.current_url


@pytest.mark.parametrize("route", GUEST_GUARDED_ROUTES)
def test_guestguard_redirects_authenticated_user_away(authenticated_driver, base_url, route):
    page = BasePage(authenticated_driver, base_url)
    page.goto(route)
    page.wait_url_contains("/dashboard")
    assert "/dashboard" in page.current_url


@pytest.mark.parametrize("route", AUTH_GUARDED_ROUTES)
def test_authguard_allows_authenticated_user_through(authenticated_driver, base_url, route):
    # The other half of the AuthGuard contract: an authenticated visitor
    # must actually reach the real route, not just avoid the /login bounce.
    page = BasePage(authenticated_driver, base_url)
    page.goto(route)
    assert "/login" not in page.current_url


@pytest.mark.parametrize("route", UNGUARDED_ROUTES)
def test_unguarded_route_reachable_without_login(unauthenticated_driver, base_url, route):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto(route)
    assert "/login" not in page.current_url, f"{route} is not guarded and must not redirect to /login"


@pytest.mark.parametrize("route", UNGUARDED_ROUTES)
def test_unguarded_route_reachable_while_authenticated(authenticated_driver, base_url, route):
    page = BasePage(authenticated_driver, base_url)
    page.goto(route)
    assert route in page.current_url or page.current_url.rstrip("/") == base_url.rstrip("/")


def test_sign_out_clears_session_and_blocks_protected_routes(base_url):
    # A dedicated, isolated Chrome session (not the shared session-scoped
    # `driver` fixture) -- this is the one real logout+re-guard round trip
    # in the whole suite, deliberately using SECOND_FIXTURE_USER rather than
    # FIXTURE_USER so a real logout here can never race or interfere with
    # any other test's shared-session login state. One extra real login is
    # well within the backend's default 10/hour/IP budget alongside the
    # single shared authenticated_driver login (see conftest.py).
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    drv = webdriver.Chrome(options=options)
    try:
        page = BasePage(drv, base_url)
        page.goto("/login")
        page.fill_id("email", SECOND_FIXTURE_USER["email"])
        page.fill_id("password", SECOND_FIXTURE_USER["password"])
        page.submit()
        page.wait_url_contains("/dashboard")

        sidebar = Sidebar(drv, base_url)
        menu = sidebar.open_user_menu(SECOND_FIXTURE_USER["display_name"])
        menu.sign_out()
        # NOT wait_url_contains("/") -- every URL contains "/", so that
        # condition is satisfied instantly and never actually waits for the
        # post-logout navigate('/', {replace:true}) to complete. Wait for
        # the one real, meaningful state change instead: /dashboard leaving
        # the URL.
        WebDriverWait(drv, 15).until(lambda d: "/dashboard" not in d.current_url)
        assert "/dashboard" not in page.current_url

        # The real point of this test: AuthGuard must reject the
        # now-cleared session on the very next protected-route visit.
        page.goto("/dashboard")
        page.wait_url_contains("/login")
        assert "/login" in page.current_url
    finally:
        drv.quit()
