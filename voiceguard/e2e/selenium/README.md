# Desktop Selenium suite

Headless Chrome against the real React frontend (docker-compose's `frontend`
service, `http://localhost:5173` by default) — this app's actual "live" test
environment. There is no separate hosted deployment: VoiceGuard is a
full-stack app (React frontend + FastAPI backend + Postgres + Redis), and
GitHub Pages can't serve any of the backend/DB, so this suite intentionally
runs against the full Docker Compose stack already brought up in CI on
every push, not a public URL. (GitHub Pages here hosts this suite's own
*report dashboards* — see "Reports & GitHub Pages" below — not the app.)

**409 real, executable test cases** (pytest's own collection count, including
parametrized instances) across 19 test modules, mapped onto real app areas
rather than a generic category taxonomy:

| Area | Test modules | Approx. count |
|---|---|---|
| Authentication & session | `test_auth.py`, `test_session_guards.py` | ~50 |
| Authorization (route guards) | `test_session_guards.py` | ~24 |
| Registration | `test_registration.py` | ~20 |
| Password recovery | `test_password_recovery.py` | ~19 |
| Navigation & shared chrome | `test_navigation.py`, `test_keyboard_navigation.py` | ~45 |
| Dashboard | `test_dashboard.py` | ~10 |
| History (CRUD: read/filter) | `test_history.py` | ~15 |
| Scan flow (CRUD: create/read + file upload) | `test_scan_flow.py` | ~23 |
| Notifications | `test_notifications.py` | ~10 |
| Onboarding | `test_onboarding.py` | ~7 |
| Help & feedback (CRUD: create) | `test_help_feedback.py` | ~19 |
| Settings (CRUD: update) | `test_settings.py` | ~24 |
| Shared result | `test_shared_result.py` | ~7 |
| Public pages / 404 | `test_public_pages.py` | ~11 |
| Accessibility | `test_accessibility.py` | ~44 |
| Error handling / input validation | `test_error_handling.py` | ~35 |
| Responsive design | `test_responsive_breakpoints.py` | ~22 |
| Performance smoke | `test_performance_smoke.py` | ~15 |

Every test exercises real, read component source (selectors/behavior taken
directly from `frontend/src/`, never guessed) against the real running
backend — no mocked responses, no fabricated data. Run
`python -m pytest --collect-only -q` for the exact current count and full
list.

## Structure

```
pages/    Page Object Model — one module per route/shared-chrome group
data/     fixture accounts + invalid-input data (same real validation rules
          as e2e/appium/data/ — same app, copied not re-derived)
tests/    test modules, one per app area (auth, registration, navigation,
          dashboard, scan flow, settings, accessibility, error handling, ...)
          plus three desktop-only modules mobile touch can't honestly cover:
          test_keyboard_navigation.py, test_responsive_breakpoints.py,
          test_performance_smoke.py
conftest.py            driver/authenticated_driver/unauthenticated_driver
                        fixtures + failure-screenshot hook
parse_results.py        selenium_report.json -> selenium_summary.json
build_html_report.py    selenium_summary.json -> execution-report.html
build_excel.py          selenium_summary.json -> Automation_Test_Report.xlsx +
                         Passed_Test_Cases.xlsx + Failed_Test_Cases.xlsx +
                         Summary_Report.xlsx
trends.html              reads history/index.json + each build's
                         selenium_summary.json client-side -> pass-rate trend
                         dashboard, published alongside execution-report.html
                         (same pattern as e2e/appium/trends.html)
```

## Running locally

Unlike the Appium suite, this one runs fine on a plain dev machine with
Docker:

```bash
docker compose up -d --build postgres redis backend frontend
cd voiceguard/e2e/selenium
pip install -r ../requirements.txt
SELENIUM_BASE_URL=http://localhost:5173 python -m pytest -v
```

`BASE_URL` is never hardcoded — the `base_url` fixture reads
`SELENIUM_BASE_URL` (defaults to `http://localhost:5173`), matching how
every page object's `goto()` uses it.

## Fixture design (read before adding tests — same reasoning as the Appium suite)

The suite shares **one** headless Chrome session (`driver`, session-scoped)
for the whole run:

- **`authenticated_driver`** (session-scoped) logs in **once** per run.
  The backend's default login rate limit is 10/hour/IP — a suite this size
  resubmitting the login form per test would fail on that alone.
- **`unauthenticated_driver`** (function-scoped) clears cookies before
  returning the shared driver. **Required** for any GuestGuard route
  (`/signup`, `/login`, `/forgot-password`, `/reset-password`) or an
  AuthGuard redirect-to-login assertion.
- Plain `driver` is safe only for genuinely unguarded routes (`/`,
  `/verify-email`, `/r/:scanId`, unknown-route 404).

**One exception**: `test_session_guards.py::test_sign_out_clears_session_and_blocks_protected_routes`
spins up its own dedicated, isolated `webdriver.Chrome()` instance (not any
of the fixtures above) and logs in as `SECOND_FIXTURE_USER` — the only real
logout round trip in the suite. Isolated deliberately, so a real
session-clearing action can never race or interfere with the shared
`authenticated_driver`'s session used by every other test.

## Priority markers

Every test module sets `pytestmark = [pytest.mark.<critical|high|medium|low>]`
(registered in `pytest.ini`), reflecting real risk — auth/session-guards are
`critical`, core flows (registration, scan flow, dashboard) are `high`,
secondary flows are `medium`, cosmetic/supporting pages are `low`.
`parse_results.py` reads this straight from pytest-json-report's `keywords`
and it flows into the `Priority` column of every Excel report — a real,
intentional signal, not a number assigned after the fact.

## CI flow (`.github/workflows/qa-suite.yml`, `selenium-tests` job)

Bring up the Docker Compose stack → wait for health → run this suite
(`--reruns 2` retry) → parse results → build the HTML report → build the
Excel reports → upload everything as the `selenium-report` artifact. This
job has **no** `continue-on-error` — it gates the pipeline normally.

**On flakiness (verified 2026-08-12, when the suite grew from ~139 to 400+
tests):** real, repeated full-suite runs against a live stack showed an
occasional single test failing — never the same test twice, and every one
of them passed cleanly when re-run in isolation — consistent with
non-deterministic timing noise from one very long-lived headless Chrome
session (see "Fixture design" above for why the session is shared, not
per-test) rather than a bug in any specific test. Every *reproducible*
failure found during that verification was root-caused and fixed in the
test/page-object code itself (stale element references on Auth-layout
pages, animation-timing races on the Settings/account and Help Center
pages, wrong fixture choice on GuestGuard-route tests, wrong assumptions
about real component text/behavior) — `--reruns 2` covers the residual,
non-reproducible ~1-2% rate, not a substitute for fixing a real bug.

`deploy-qa-reports` (a separate job) then publishes both this suite's and
the Appium suite's reports to GitHub Pages side by side:
`reports/selenium/latest/` + `reports/selenium/history/build-N/` for this
suite, `reports/latest/` + `reports/history/build-N/` for Appium's
(unchanged, to preserve the URL already in use).

## Reports & GitHub Pages

Every `selenium-tests` run produces, in `voiceguard/e2e/results/`:
`selenium_report.json`/`.xml` (raw pytest-json-report/JUnit),
`selenium_summary.json` (parsed totals + module breakdown + priority
breakdown + failures), `execution-results.json` (a plain copy of
`selenium_summary.json` under that name, for the deliverable-spec's
requested filename), `summary.md` (the same Markdown table
`report_summary_markdown.py` prints to the `summary` job's
`$GITHUB_STEP_SUMMARY`, saved as a real file), `execution-report.html`,
`Automation_Test_Report.xlsx` (6 sheets: Executed, Passed, Failed, Skipped,
Execution Metrics, Defect Summary), `Passed_Test_Cases.xlsx`,
`Failed_Test_Cases.xlsx`, `Summary_Report.xlsx`, and `screenshots/`
(failures only, prefixed `selenium_` to stay distinct from Appium's in the
shared results dir). `reports/build_master_test_report.py` (repo root)
already reads `selenium_report.json` generically into the cross-discipline
`VoiceGuard_App_Testing_Report.xlsx` — no changes needed there.

`trends.html` (this directory) is a pass-rate trend dashboard across recent
CI runs — same static-page-reads-a-JSON-manifest pattern as
`e2e/appium/trends.html`, published to `reports/selenium/latest/trends.html`
by `deploy-qa-reports`.

Live reports:
- `https://amit-0000.github.io/AMIT-KRISHNA/reports/selenium/latest/execution-report.html`
- `https://amit-0000.github.io/AMIT-KRISHNA/reports/selenium/latest/trends.html`

## Troubleshooting

- **A GuestGuard-page test unexpectedly redirects to `/dashboard`**: it's
  using plain `driver` instead of `unauthenticated_driver` — see "Fixture
  design" above.
- **A test fails only in CI, not locally**: check `execution-report.html`
  in the `selenium-report` artifact for the captured screenshot and failure
  reason first — CI's Docker Compose stack and a local one should behave
  the same, but timing (health-check readiness, model inference latency)
  can differ.
- **Responsive-breakpoint tests fail after a Tailwind config change**:
  `test_responsive_breakpoints.py` asserts against the real breakpoint
  pixel values found in the frontend's layout components — if those
  change, update the test's constants to match, don't just widen the
  assertion.
