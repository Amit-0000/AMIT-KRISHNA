"""Mobile-web coverage of the public /r/:scanId page
(frontend/src/pages/SharedResult/index.tsx) — no AuthGuard, no AppShell.
No real shared-scan link exists to test the success path against (public
sharing has no self-serve "share this scan" UI trigger in the frontend at
all yet — SharedResultPage.tsx's own copy says "Public sharing is still
rolling out"), so this covers the one real, deterministic path: an
unavailable/unknown share link."""
from __future__ import annotations

import uuid

from pages.shared_result_page import SharedResultPage


def test_shared_result_unknown_scan_shows_unavailable(driver, base_url):
    page = SharedResultPage(driver, base_url)
    page.goto_shared_result(str(uuid.uuid4()))
    assert page.is_unavailable()


def test_shared_result_go_to_voiceguard_link_navigates_home(driver, base_url):
    page = SharedResultPage(driver, base_url)
    page.goto_shared_result(str(uuid.uuid4()))
    page.tap(page.find_clickable(*page.GO_TO_VOICEGUARD_LINK))
    assert page.current_url.rstrip("/") == page.base_url.rstrip("/")


def test_shared_result_page_requires_no_login(unauthenticated_driver, base_url):
    page = SharedResultPage(unauthenticated_driver, base_url)
    page.goto_shared_result(str(uuid.uuid4()))
    assert "/r/" in page.current_url, "unguarded /r/:scanId must not redirect to /login"
