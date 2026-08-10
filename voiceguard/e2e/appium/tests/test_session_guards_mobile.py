"""Mobile-web coverage of the two route guards that redirect
(frontend/src/guards/AuthGuard.tsx, GuestGuard.tsx):
  - AuthGuard: unauthenticated visitor to a protected route -> /login
  - GuestGuard: authenticated visitor to a guest-only route -> /dashboard

OnboardingGuard (frontend/src/guards/OnboardingGuard.tsx) is NOT covered
here: exercising its real redirect needs an authenticated session for a user
whose onboarding_completed is still false, which requires a freshly
registered *and verified* account — verification needs a real token, out of
reach for this suite for the same reason noted in
test_password_recovery_mobile.py (reserved for the DAST suite's docker-logs
mechanism). Not faked here.
"""
from __future__ import annotations

import pytest

from pages.base_page import BasePage

AUTH_GUARDED_ROUTES = ["/dashboard", "/history", "/settings/profile", "/feedback"]
GUEST_GUARDED_ROUTES = ["/login", "/signup", "/forgot-password", "/reset-password"]


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
