"""Shared fixtures for the desktop Selenium web E2E suite.

Runs headless Chrome against the frontend dev server (docker-compose's
`frontend` service, http://localhost:5173 by default) and reuses the DAST
fixture accounts (automated_test/setup_env.py) for the authenticated flows,
so this suite doesn't need its own signup/verify bootstrapping.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urllib3.exceptions import HTTPError as Urllib3HTTPError

# Lets test modules do `from pages.base_page import BasePage` / `from data.users
# import ...` regardless of how/where pytest is invoked from — same reasoning
# as voiceguard/e2e/appium/conftest.py's identical line.
sys.path.insert(0, str(Path(__file__).parent))

from data.users import FIXTURE_USER  # noqa: E402
from screenshot_naming import screenshot_stem  # noqa: E402

# Substrings of a WebDriverException message that mean the underlying Chrome
# session itself is gone (crashed tab, killed renderer, dropped devtools
# connection) rather than a normal, in-page failure (stale element, timeout,
# etc.) that a fresh command against the *same* session could still recover
# from. Used by ResilientDriver below.
_DEAD_SESSION_MARKERS = (
    "invalid session id",
    "session deleted",
    "session not created",
    "tab crashed",
    "chrome not reachable",
    "disconnected: not connected to devtools",
    "target window already closed",
)

# Exception types ResilientDriver treats as possibly-recoverable-via-
# relaunch. Urllib3HTTPError (MaxRetryError, NewConnectionError, etc.) is
# what actually surfaces — not a WebDriverException — if the chromedriver
# *process* itself is gone, not just the browser/tab inside it (confirmed
# live: driver.quit() followed by any further call raises
# urllib3.exceptions.MaxRetryError, unwrapped, all the way up through
# selenium's remote_connection.py). Any such connection-level error always
# means the session is unreachable — unlike WebDriverException, which also
# covers ordinary in-page failures, so those still need the marker-string
# check below to avoid treating e.g. a stale-element error as fatal.
_RECOVERABLE_EXCEPTION_TYPES = (WebDriverException, Urllib3HTTPError)


def _is_dead_session_error(exc: Exception) -> bool:
    if isinstance(exc, Urllib3HTTPError):
        return True
    return any(marker in str(exc).lower() for marker in _DEAD_SESSION_MARKERS)

BASE_URL = os.environ.get("SELENIUM_BASE_URL", "http://localhost:5173")
REPO_ROOT = Path(__file__).resolve().parents[3]
INPUT_JSON = REPO_ROOT / "automated_test" / "input.json"

# e2e/results/, shared with the Appium suite's identical output directory
# (and where selenium_report.json already lands) — parse_results.py/
# build_html_report.py/build_excel.py and this suite's screenshots all live
# next to each other, same convention as e2e/appium/conftest.py.
RESULTS_DIR = Path(__file__).parent.parent / "results"
SCREENSHOTS_DIR = RESULTS_DIR / "screenshots"


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


def _launch_chrome() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(2)
    return drv


class ResilientDriver:
    """Transparently relaunches Chrome if the shared session dies mid-run.

    Confirmed live, across three separate real CI runs of this 409-test
    suite (each on a resource-constrained GitHub-hosted runner sharing one
    long-lived headless Chrome session for the whole run): the session can
    die outright partway through — InvalidSessionIdException at one point,
    a literal "tab crashed" WebDriverException at another, on unmodified
    Chrome/chromedriver versions the runner image happened to have that day
    — and once it does, *every* later command against that driver fails the
    same way, cascading into hundreds of unrelated test failures with no
    way to recover short of a fresh browser process. That's a materially
    worse outcome than a handful of genuinely-flaky individual tests, so
    it's worth containing even without a confirmed root cause for why the
    session dies in the first place.

    A plain "relaunch inside the driver fixture" doesn't work: driver is
    session-scoped, and pytest caches a session-scoped fixture's *return
    value* for the whole run, so every fixture that already received the
    old (now-dead) webdriver.Chrome reference would keep using it forever.
    This wraps that reference in a proxy with a stable identity instead —
    every attribute/method access goes through __getattr__/the returned
    wrapper, which retries once against a freshly-launched Chrome instance
    if the first attempt fails with a dead-session error, so the swap is
    invisible to callers (page objects, WebDriverWait, EC conditions, etc.
    all just call ordinary methods/properties on whatever `driver` object
    they were given).

    The test that actually witnesses a crash will still fail (there's no
    reasonable way to resume it mid-navigation on a brand new browser), but
    pytest-rerunfailures (already enabled, --reruns 2) retries it, and by
    then this proxy has already healed — containing the blast radius to
    that one test (plus reruns) instead of the rest of the suite.
    """

    def __init__(self, launch):
        self._launch = launch
        self._real = launch()
        self.relaunch_count = 0

    def _relaunch(self) -> None:
        try:
            self._real.quit()
        except Exception:  # noqa: BLE001 - the old session is already broken; nothing to act on
            pass
        self._real = self._launch()
        self.relaunch_count += 1

    def __getattr__(self, name):
        try:
            attr = getattr(self._real, name)
        except _RECOVERABLE_EXCEPTION_TYPES as exc:
            if not _is_dead_session_error(exc):
                raise
            self._relaunch()
            attr = getattr(self._real, name)

        if not callable(attr):
            return attr

        def call_with_recovery(*args, **kwargs):
            try:
                return getattr(self._real, name)(*args, **kwargs)
            except _RECOVERABLE_EXCEPTION_TYPES as exc:
                if not _is_dead_session_error(exc):
                    raise
                self._relaunch()
                return getattr(self._real, name)(*args, **kwargs)

        return call_with_recovery

    def quit(self) -> None:
        self._real.quit()


@pytest.fixture(scope="session")
def driver():
    # Session-scoped: a plain headless Chrome launch is cheap (unlike
    # Appium's UiAutomator2 session), but authenticated_driver below still
    # needs one shared browser to log in on *once* rather than once per
    # test — see its docstring for why. Reusing one driver for the whole
    # run also avoids ~120 separate Chrome process launches.
    #
    # Wrapped in ResilientDriver, not a bare webdriver.Chrome — see its
    # docstring for why a plain session-scoped instance can't recover from
    # a mid-run Chrome crash on its own.
    resilient = ResilientDriver(_launch_chrome)
    yield resilient
    resilient.quit()


@pytest.fixture
def authenticated_driver(driver, base_url):
    # Function-scoped, but idempotent: the login sequence below only runs
    # if the shared driver doesn't already show a valid access_token
    # cookie, so in the common case (already logged in) a request costs one
    # cheap cookie check, not a real login. This is what lets
    # ResilientDriver's crash recovery (see the driver fixture) actually
    # work end to end -- pytest caches a *session-scoped* fixture's return
    # value for the whole run, so a session-scoped version of this fixture
    # would keep returning the pre-crash "I already logged in" state
    # forever even after ResilientDriver transparently relaunches Chrome
    # (which starts with no cookies at all) — this fixture would never
    # re-run its login, and every later authenticated_driver test would
    # silently get a logged-out browser. Checking (and only actually
    # logging in when needed) on every request is what makes a freshly
    # relaunched Chrome instance get logged back in automatically. The
    # login sequence itself, and everything below about *why* it's shaped
    # the way it is, is otherwise unchanged from the original
    # session-scoped-only version — same two real constraints as Appium's
    # identical fixture:
    # (1) the backend's default login rate limit is 10/hour/IP (see
    # performance/docker-compose.loadtest.yml's override note) — a suite
    # this size resubmitting the login form per test would blow through
    # that budget on infra grounds having nothing to do with app
    # correctness; (2) driver is a single shared browser session, so a
    # second real submission while already authenticated races GuestGuard's
    # redirect-away-from-/login (frontend/src/guards/GuestGuard.tsx).
    # Explicit waits, not bare find_element + the driver's 2s implicit
    # wait: confirmed live that this fixture's very first invocation, when
    # it happens to run right after an unauthenticated_driver test's
    # teardown navigation (driver.get(base_url) to restore cookie state),
    # can hit a StaleElementReferenceException on the email field — a race
    # between that teardown's navigation settling and this setup's own
    # driver.get("/login") + immediate find_element, not something the
    # implicit wait reliably absorbs.
    #
    # Root-caused live (see e2e/selenium/../repro notes) why this fixture's
    # first invocation can fail specifically when it lands right after
    # test_session_guards.py's 10-case AuthGuard parametrization: each of
    # those cycles ends on an AuthGuard-triggered client-side redirect to
    # /login carrying router state (`<Navigate to="/login" state={{from:
    # <route>}} />`, frontend/src/guards/AuthGuard.tsx) — a *client-side*
    # navigation, so it's `history.replaceState`, not a real browser
    # navigation. If the very next thing this fixture does is
    # `driver.get(f"{base_url}/login")` and the browser is *already sitting
    # on that exact URL* (true here — the 10th AuthGuard cycle's redirect
    # target), Chrome treats it as a same-URL reload and preserves the
    # existing `history.state` rather than clearing it, confirmed live via
    # `window.history.state` before/after. GuestGuard then legitimately
    # honors that leftover `state.from` on successful login
    # (frontend/src/guards/GuestGuard.tsx — this part is correct, desired
    # product behavior: return the user to the page they originally wanted)
    # and redirects to whatever AuthGuard route the 10th cycle happened to
    # test last instead of /dashboard — which is exactly what this fixture
    # waits for, hence the timeout. Not an auth failure, not app-code worth
    # changing (the from-redirect is correct); the fixture's own assumption
    # that "navigate to /login" always starts from a state-less history
    # entry is what's wrong. Fixed by bouncing through a neutral route
    # first so the /login entry this fixture actually types into is always
    # a fresh one with no router state to inherit, regardless of what the
    # browser was doing right before.
    if not any(c["name"] == "access_token" for c in driver.get_cookies()):
        driver.get(base_url)
        driver.get(f"{base_url}/login")
        WebDriverWait(driver, 15).until(EC.visibility_of_element_located(("id", "email"))).send_keys(
            FIXTURE_USER["email"]
        )
        WebDriverWait(driver, 15).until(EC.visibility_of_element_located(("id", "password"))).send_keys(
            FIXTURE_USER["password"]
        )
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(("css selector", "button[type=submit]"))
        ).click()
        WebDriverWait(driver, 15).until(EC.url_contains("/dashboard"))
    return driver


@pytest.fixture
def unauthenticated_driver(driver, base_url):
    """For tests that need a guest (logged-out) view of a GuestGuard-protected
    page (/signup, /login, /forgot-password, /reset-password) or that assert
    AuthGuard's redirect-to-/login behavior. Clears the shared driver's
    session cookies rather than assuming the browser starts each test
    logged out — it won't, once any test in this run has used
    authenticated_driver.

    Restores those cookies on teardown instead of leaving the browser
    logged out — confirmed necessary by a real full-suite run: without this,
    every authenticated_driver test that happened to run after ANY
    unauthenticated_driver test in collection order silently got a
    logged-out browser (authenticated_driver only re-logs-in when its own
    idempotency check finds no access_token cookie present — see its
    docstring — so a browser left logged out here would otherwise stay that
    way), got redirected to /login by AuthGuard, and timed out waiting for
    content that could never appear. Restoring via saved cookies rather
    than a real re-login keeps the same rate-limit
    protection authenticated_driver exists for.

    get_cookies()/delete_all_cookies() only see cookies visible from the
    *current page's path*, and this backend deliberately scopes its
    refresh_token cookie to path=/api/v1/auth (api/auth/service.py's
    REFRESH_COOKIE_PATH) — a path the frontend SPA itself never navigates to.
    Calling those from an ordinary frontend route therefore never actually
    deleted refresh_token; it stayed live in the browser, and the frontend
    HTTP client's own 401 -> silent-refresh-via-POST-/api/v1/auth/refresh
    flow used it to transparently re-authenticate mid-test the moment any
    guest-page auth check 401'd — so a "logged out" guest test could
    intermittently (and, once enough of the suite had run and timing lined
    up, deterministically) render as a fully authenticated user instead of
    the guest page under test (confirmed via screenshots of a real full-suite
    run). _COOKIE_SCOPE_PATH below is a route that doesn't exist on the
    backend (any 404 there is fine — nothing reads the response) but is
    still same-origin (proxied through vite, see frontend/vite.config.ts's
    /api proxy) and under /api/v1/auth, which makes refresh_token visible to
    the read+clear that follows while the browser briefly sits there.

    Only ONE extra navigation per test, at setup — not two. Two earlier
    fixes were each tried against a real CI run and rejected:
    - A Chrome DevTools Protocol version (Network domain's getAllCookies/
      clearBrowserCookies/setCookies, none of which are path-scoped) avoids
      the extra navigation entirely, but reliably crashed the shared Chrome
      session outright (InvalidSessionIdException) after roughly a dozen
      uses in CI — worse than the bug it fixed.
    - A version with a second extra navigation at teardown (to re-visit
      _COOKIE_SCOPE_PATH before restoring) avoided the CDP crash but still
      left the CI run crashing early via a Chrome "tab crashed" error,
      consistent with the doubled per-test navigation load straining an
      already resource-constrained CI runner over a 400+-test single
      session.
    Confirmed empirically (against the real backend) that add_cookie() is
    NOT path-restricted the way get_cookies()/delete_all_cookies() are —
    setting a cookie for a given path works from anywhere, only *reading or
    deleting* one requires being on a matching path. So teardown restores
    directly via add_cookie() with no navigation at all. This can't be
    simplified further by only reading+caching the real refresh_token once
    per whole run instead of once per test: the backend rotates
    refresh_token on every use (api/auth/service.py's rotate_refresh_token)
    and treats reuse of an already-rotated token as a theft signal that
    revokes every session for the user — restoring a stale cached value
    after any silent refresh happened elsewhere in the run would be actively
    wrong, not just less correct, so the current real value has to be
    re-read fresh at each test's own setup.
    """
    _COOKIE_SCOPE_PATH = "/api/v1/auth/__selenium_cookie_scope__"
    driver.get(f"{base_url}{_COOKIE_SCOPE_PATH}")
    saved_cookies = driver.get_cookies()
    driver.delete_all_cookies()
    yield driver
    # No navigation here (see the docstring): add_cookie() isn't
    # path-restricted, so each saved cookie can be written back directly
    # from wherever the test body left the browser, overwriting whatever
    # (if anything) is currently there for that name+path.
    for cookie in saved_cookies:
        try:
            driver.add_cookie(cookie)
        except WebDriverException:
            # Best-effort per-cookie: one incompatible cookie attribute
            # must not stop the rest of the session from being restored.
            pass


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # Only the "call" phase (not setup/teardown) reflects an actual test
    # failure worth a screenshot — a fixture error in "setup" has no
    # meaningful page state to capture yet.
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return

    drv = item.funcargs.get("driver") or item.funcargs.get("authenticated_driver")
    if drv is None:
        return

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = screenshot_stem(item.nodeid)
    try:
        # "selenium_" prefix keeps filenames distinct from the Appium
        # suite's screenshots in the same shared results/screenshots/ dir,
        # even though CI uploads them as separate artifacts anyway.
        drv.save_screenshot(str(SCREENSHOTS_DIR / f"selenium_{safe_name}.png"))
    except WebDriverException:
        # Best-effort: a screenshot failure must never mask the real test
        # failure this hook is reacting to.
        pass
