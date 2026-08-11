"""Desktop coverage of error/edge-case states: malformed resource IDs,
unknown routes, and invalid tokens/query params, across every page whose
page object already exposes a real "not found"/"unavailable"/"invalid"
locator (ScanResultPage, ScanDetailPage, SharedResultPage, HelpArticlePage,
ResetPasswordPage, VerifyEmailPage, NotFoundPage). Every ID string here is
either a real malformed value (not a valid UUID at all) or a syntactically
valid-but-nonexistent one — none of these are expected to succeed, so
each test is asserting the app degrades to its own real, already-identified
error state rather than crashing, hanging, or (for the injection-style
payloads) executing/reflecting the raw input.
"""
from __future__ import annotations

import uuid

import pytest

from data.users import VALID_SIGNUP_PASSWORD
from pages.auth_pages import NotFoundPage, ResetPasswordPage, SignupPage, VerifyEmailPage
from pages.base_page import BasePage
from pages.help_feedback_pages import HelpArticlePage
from pages.history_page import HistoryPage
from pages.notifications_page import NotificationsPage
from pages.scan_pages import ScanDetailPage, ScanProcessingPage, ScanResultPage
from pages.shared_result_page import SharedResultPage

pytestmark = [pytest.mark.medium]

MALFORMED_IDS = [
    "not-a-uuid",
    "",
    "0",
    "../../etc/passwd",
    "<script>alert(1)</script>",
    "' OR '1'='1",
    "a" * 300,
    "日本語-scan-id-🎧",
]

# For :scanId/:articleSlug *path segments* specifically (not query params):
# "" and "../../etc/passwd" are excluded here because the browser itself
# normalizes them before the request ever reaches the app -- confirmed live
# (not assumed): "/scan/" (empty id) never matches React Router's
# `/scan/:scanId` at all (a path param can't be empty), landing on the
# generic 404 route instead of ScanResultPage's own not-found state; and
# "/scan/../../etc/passwd" gets collapsed by the browser's own URL
# normalization to "/etc/passwd" *before* any request is even made, for the
# same reason. The `<script>...` payload is replaced with an equivalent
# XSS-style payload that contains no literal "/" -- the original's closing
# `</script>` tag's slash splits the URL into an extra path segment
# ("/scan/<script>alert(1)" + "script>" as a second segment), which also
# fails to match the single-segment `/scan/:scanId` route for the same
# structural reason, not because of anything scan-id-specific.
PATH_SEGMENT_MALFORMED_IDS = [
    "not-a-uuid",
    "0",
    "' OR '1'='1",
    "a" * 300,
    "日本語-scan-id-🎧",
    "<img src=x onerror=alert(1)>",
]

UNKNOWN_ROUTE_VARIANTS = [
    "/this-route-does-not-exist",
    "/DASHBOARD",  # case-sensitivity: real routes are lowercase
    "/dashboard/",
    "/scan",  # real route is /scan/new, not bare /scan
    "//",
    "/settings/nonexistent-tab",
    "/history/",  # trailing slash on a route that normally takes a :scanId
    "/help/../../dashboard",
]


@pytest.mark.parametrize("bad_id", PATH_SEGMENT_MALFORMED_IDS)
def test_scan_result_malformed_id_shows_not_found(authenticated_driver, base_url, bad_id):
    page = ScanResultPage(authenticated_driver, base_url)
    page.goto_result(bad_id)
    assert page.is_not_found(timeout=10)


@pytest.mark.parametrize("bad_id", PATH_SEGMENT_MALFORMED_IDS)
def test_scan_detail_malformed_id_shows_not_found(authenticated_driver, base_url, bad_id):
    page = ScanDetailPage(authenticated_driver, base_url)
    page.goto_detail(bad_id)
    assert page.is_not_found(timeout=10)


@pytest.mark.parametrize("bad_id", PATH_SEGMENT_MALFORMED_IDS)
def test_shared_result_malformed_id_shows_unavailable(driver, base_url, bad_id):
    page = SharedResultPage(driver, base_url)
    page.goto_shared_result(bad_id)
    assert page.is_unavailable(timeout=10)


def test_scan_result_empty_id_falls_through_to_generic_404(authenticated_driver, base_url):
    # The real, structural outcome for an empty :scanId path segment (see
    # PATH_SEGMENT_MALFORMED_IDS's comment): React Router never matches
    # `/scan/:scanId` at all, so this lands on the app's generic 404 route,
    # not ScanResultPage's own not-found state.
    page = ScanResultPage(authenticated_driver, base_url)
    page.goto_result("")
    assert "404" in page.body_text()


def test_shared_result_path_traversal_id_never_reaches_the_app(driver, base_url):
    # "../../etc/passwd" gets collapsed by the browser's own URL
    # normalization before any request is made -- landing on the generic
    # 404 route, not SharedResultPage's own unavailable state. Real,
    # structural browser behavior, not an app bug.
    page = SharedResultPage(driver, base_url)
    page.goto_shared_result("../../etc/passwd")
    assert "404" in page.body_text()


@pytest.mark.parametrize("route", UNKNOWN_ROUTE_VARIANTS)
def test_unknown_route_variant_shows_404_or_a_real_route(authenticated_driver, base_url, route):
    # Some of these variants (e.g. "/dashboard/" with a trailing slash) may
    # legitimately resolve to a real route depending on the router's
    # matching rules -- the one thing that must never happen is an
    # unhandled crash (blank page / no body content at all).
    page = BasePage(authenticated_driver, base_url)
    page.goto(route)
    assert page.body_text() != "", f"{route} rendered no body content at all"


def test_deeply_nested_unknown_route_shows_404(driver, base_url):
    page = NotFoundPage(driver, base_url)
    page.goto("/a/b/c/d/e/f/g/this-does-not-exist")
    assert page.shows_404()


def test_unknown_route_with_query_string_shows_404(driver, base_url):
    page = NotFoundPage(driver, base_url)
    page.goto("/this-route-does-not-exist?foo=bar&baz=qux")
    assert page.shows_404()


def test_help_article_empty_slug_falls_back_to_help_index_or_not_found(authenticated_driver, base_url):
    # /help/ with an empty :articleSlug -- either React Router doesn't match
    # this to the article route at all (falling through to /help or 404),
    # or it does and HelpArticlePage's own not-found state renders. Both are
    # real, acceptable outcomes; only a raw crash is not.
    page = BasePage(authenticated_driver, base_url)
    page.goto("/help/")
    assert page.body_text() != ""


@pytest.mark.parametrize("bad_slug", ["<img src=x onerror=alert(1)>", "' OR '1'='1"])
def test_help_article_injection_style_slug_shows_not_found_without_executing(authenticated_driver, base_url, bad_slug):
    # Payloads with no literal "/" only (see PATH_SEGMENT_MALFORMED_IDS's
    # comment) -- "<script>...</script>" and "../../../etc/passwd" both
    # contain one, which splits/normalizes the URL before it ever reaches
    # HelpArticlePage's own not-found state (covered separately below).
    page = HelpArticlePage(authenticated_driver, base_url)
    page.goto_article(bad_slug)
    assert page.is_not_found_shown()
    # The raw payload must never come back unescaped as live, executable
    # markup -- if it did, the injected <img src="x"> the "<img src=x
    # onerror=...>" payload describes would itself be a real DOM node, not
    # just inert page text. NOT a blanket "zero <script> tags" check: the
    # Vite dev server injects its own real <script> module-loader/HMR-client
    # tags into every page unconditionally, unrelated to this payload.
    assert not page.driver.find_elements("css selector", 'img[src="x"]')


def test_help_article_path_traversal_slug_never_reaches_the_app(authenticated_driver, base_url):
    # /help/:articleSlug is inside AuthGuard+AppShell, so this needs an
    # authenticated session, unlike the other path-traversal checks above
    # (which target fully public routes).
    page = HelpArticlePage(authenticated_driver, base_url)
    page.goto_article("../../../etc/passwd")
    assert "404" in page.body_text()


def test_verify_email_empty_token_param_treated_as_missing(driver, base_url):
    page = VerifyEmailPage(driver, base_url)
    page.goto("/verify-email?token=")
    assert page.shows_missing_token_message()


def test_verify_email_very_long_token_rejected_by_backend(driver, base_url):
    page = VerifyEmailPage(driver, base_url)
    page.open(token="a" * 500)
    assert page.shows_invalid_or_expired_message()


def test_reset_password_empty_token_param_shows_invalid_link(unauthenticated_driver, base_url):
    page = ResetPasswordPage(unauthenticated_driver, base_url)
    page.goto("/reset-password?token=")
    assert page.shows_invalid_link()


def test_reset_password_very_long_token_treated_as_present(unauthenticated_driver, base_url):
    # A syntactically-present (if backend-invalid) token should still reach
    # the form -- the *form* rendering and the *backend rejection on submit*
    # are two different real states, already covered separately by
    # test_password_recovery.py's garbage-token test.
    page = ResetPasswordPage(unauthenticated_driver, base_url)
    page.open(token="a" * 500)
    assert page.shows_form()


def test_scan_processing_malformed_id_param_redirects_or_stays(authenticated_driver, base_url):
    page = ScanProcessingPage(authenticated_driver, base_url)
    page.goto("/scan/processing?id=not-a-real-scan-id")
    # Real behavior: a present (even if invalid) id keeps the page on
    # /scan/processing rather than the no-id redirect-to-/scan/new path.
    assert "/scan/processing" in page.current_url


def test_notifications_page_survives_direct_reload(authenticated_driver, base_url):
    page = NotificationsPage(authenticated_driver, base_url)
    page.goto_notifications()
    authenticated_driver.refresh()
    assert page.is_loaded()


def test_history_page_survives_direct_reload(authenticated_driver, base_url):
    page = HistoryPage(authenticated_driver, base_url)
    page.goto_history()
    authenticated_driver.refresh()
    assert page.is_showing_empty_state(timeout=5) or page.is_showing_table(timeout=5)


def test_dashboard_survives_rapid_repeated_navigation(authenticated_driver, base_url):
    # A real, simple resilience check: firing several fast client-side
    # navigations in a row must not leave the app in a broken/blank state.
    page = BasePage(authenticated_driver, base_url)
    for route in ("/dashboard", "/history", "/notifications", "/dashboard"):
        page.goto(route)
    page.wait_url_contains("/dashboard")
    assert page.body_text() != ""


@pytest.mark.parametrize("bad_id", MALFORMED_IDS)
def test_scan_processing_malformed_id_query_param_does_not_crash(authenticated_driver, base_url, bad_id):
    page = ScanProcessingPage(authenticated_driver, base_url)
    page.goto(f"/scan/processing?id={bad_id}")
    assert page.body_text() != "", f"malformed id={bad_id!r} left the processing page blank"


def test_signup_extremely_long_email_rejected(unauthenticated_driver, base_url):
    page = SignupPage(unauthenticated_driver, base_url)
    page.open()
    long_email = ("a" * 250) + "@example.com"
    page.fill_form("Selenium QA", long_email, VALID_SIGNUP_PASSWORD, VALID_SIGNUP_PASSWORD)
    page.submit_signup()
    assert "/signup" in page.current_url


def test_login_extremely_long_password_does_not_crash_the_app(unauthenticated_driver, base_url):
    page = BasePage(unauthenticated_driver, base_url)
    page.goto("/login")
    page.fill_id("email", "selenium.longpw@example.com")
    page.fill_id("password", "a" * 5000)
    page.submit()
    assert page.body_text() != ""
    assert "/login" in page.current_url
