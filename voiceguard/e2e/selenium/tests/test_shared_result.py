"""Desktop coverage of the public /r/:scanId page
(frontend/src/pages/SharedResult/index.tsx) — no AuthGuard, no AppShell.
No real shared-scan link exists to test the success path against (public
sharing has no self-serve "share this scan" UI trigger in the frontend at
all yet — SharedResultPage.tsx's own copy says "Public sharing is still
rolling out"), so this covers the one real, deterministic path: an
unavailable/unknown share link."""
from __future__ import annotations

import uuid

import pytest

from pages.shared_result_page import SharedResultPage

pytestmark = [pytest.mark.medium]


def test_shared_result_unknown_scan_shows_unavailable(driver, base_url):
    page = SharedResultPage(driver, base_url)
    page.goto_shared_result(str(uuid.uuid4()))
    assert page.is_unavailable()


def test_shared_result_go_to_voiceguard_link_navigates_home(driver, base_url):
    page = SharedResultPage(driver, base_url)
    page.goto_shared_result(str(uuid.uuid4()))
    page.click(page.find_clickable(*page.GO_TO_VOICEGUARD_LINK))
    assert page.current_url.rstrip("/") == page.base_url.rstrip("/")


def test_shared_result_page_requires_no_login(unauthenticated_driver, base_url):
    page = SharedResultPage(unauthenticated_driver, base_url)
    page.goto_shared_result(str(uuid.uuid4()))
    assert "/r/" in page.current_url, "unguarded /r/:scanId must not redirect to /login"


def test_shared_result_reachable_while_authenticated_too(authenticated_driver, base_url):
    # /r/:scanId has no guard at all (App.tsx) -- an authenticated session
    # must not change this route's reachability either.
    page = SharedResultPage(authenticated_driver, base_url)
    page.goto_shared_result(str(uuid.uuid4()))
    assert page.is_unavailable()


def test_shared_result_malformed_scan_id_still_shows_unavailable(driver, base_url):
    # Not a valid UUID at all -- the page must degrade to the same real
    # "unavailable" state rather than crashing or hanging.
    page = SharedResultPage(driver, base_url)
    page.goto_shared_result("not-a-uuid-at-all")
    assert page.is_unavailable()


def test_shared_result_go_to_voiceguard_link_has_href_to_root(driver, base_url):
    page = SharedResultPage(driver, base_url)
    page.goto_shared_result(str(uuid.uuid4()))
    link = page.find_clickable(*page.GO_TO_VOICEGUARD_LINK)
    assert link.get_attribute("href").rstrip("/") == page.base_url.rstrip("/")
