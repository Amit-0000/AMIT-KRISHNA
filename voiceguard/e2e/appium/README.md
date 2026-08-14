# Appium mobile-web suite

VoiceGuard has **no native Android app** — this suite drives the same React
frontend as `voiceguard/e2e/selenium/`, but through Appium's UiAutomator2
driver controlling real mobile Chrome on an Android emulator, exercising the
responsive/mobile-viewport UI path (touch events, mobile viewport CSS,
mobile Chrome quirks) that desktop Selenium can't reach.

## Structure

```
pages/    Page Object Model — one module per route/shared-chrome group
data/     fixture accounts + invalid-input data (real validation rules from
          frontend/src/lib/validation.ts, not guessed)
tests/    test modules, one per app area (auth, registration, navigation,
          dashboard, scan flow, settings, ...)
conftest.py               driver/authenticated_driver/unauthenticated_driver
                           fixtures + failure-screenshot hook
parse_results.py          appium_report.json -> appium_summary.json
build_html_report.py      appium_summary.json -> execution-report.html
check_pass_threshold.py   appium_summary.json -> real pass/fail gate for the
                           appium-tests job (APPIUM_MIN_PASS_RATE, default 90)
update_history_manifest.py  maintains reports/history/index.json on gh-pages
report_summary_markdown.py  prints real numbers into $GITHUB_STEP_SUMMARY
trends.html                static page, fetches history/*/appium_summary.json
```

## Running locally

You can't, on a plain dev machine — this suite needs a running Appium
server + Android emulator (Android SDK), which this suite treats as CI-only
(see `conftest.py`'s docstring). You *can* sanity-check the suite without
either:

```bash
cd voiceguard/e2e/appium
pip install -r ../requirements.txt
python -m pytest --collect-only -q   # verifies imports/syntax, no driver needed
```

## Fixture design (read before adding tests)

The suite shares **one** Appium session (`driver`, session-scoped) for the
whole run — creating it is the expensive part (2-9 min under CI's 2-vCPU
runner). Because of that:

- **`authenticated_driver`** (session-scoped) logs in **once** per run, not
  once per test. The backend's default login rate limit is 10/hour/IP — a
  suite this size resubmitting the login form per test would fail on that
  alone, unrelated to app correctness.
- **`unauthenticated_driver`** (function-scoped) clears cookies on the
  shared driver before returning it. **Required** for any test hitting a
  GuestGuard route (`/signup`, `/login`, `/forgot-password`,
  `/reset-password`) or an AuthGuard redirect-to-login assertion — some
  earlier test in this ~100-test run will already have triggered
  `authenticated_driver`, so you cannot rely on file/collection order to
  keep the shared browser logged out.
- Plain `driver` is safe only for genuinely unguarded routes (`/`,
  `/verify-email`, `/r/:scanId`, unknown-route 404).

## CI flow (`.github/workflows/qa-suite.yml`, `appium-tests` job)

AVD cache warm-up → bring up the Docker stack → start Appium → run this
suite on `reactivecircus/android-emulator-runner` (with `--reruns 1` test-
level retry, i.e. 2 attempts per test) → parse results → build the HTML
report → **apply a real pass-rate threshold gate** (`check_pass_threshold.py`,
`APPIUM_MIN_PASS_RATE`, default 90) → upload everything as the
`appium-report` artifact. A separate `deploy-qa-reports` job then publishes
that artifact to GitHub Pages (`reports/latest/` + an appended
`reports/history/build-<run>/`).

This job gates the pipeline like any other job in this workflow — its
result reflects the real outcome, not a masked `continue-on-error: true`.
Only the pytest-run step itself tolerates a non-zero exit (step-level
`continue-on-error`, so a handful of failing/flaky tests don't abort the run
before the threshold check and report/artifact steps get to run);
`check_pass_threshold.py` is what actually decides pass/fail, and a genuine
infra failure (no report produced at all, or zero tests executed) still
fails the job. It previously carried a job-level `continue-on-error: true`
while 5 real root causes of Android-emulator flakiness on GitHub's shared
2-vCPU runners were investigated and fixed one at a time (cold KVM boot
timing, redundant session creation, under-sized instrumentation timeouts, a
broken chromedriver auto-download pairing, and system-server startup
ordering under CPU contention, guarded by the `service check settings` wait
loop) — see the job's inline comment before touching any of that setup, the
emulator caching, chromedriver pinning, and timeouts are tuned against
measured CI behavior, not defaults.

If a test itself fails (not the infra), `execution-report.html` links a
failure screenshot (`results/screenshots/<test>.png`, captured by
`conftest.py`'s `pytest_runtest_makereport` hook) and the parsed failure
reason.

## Reports & GitHub Pages

Every `appium-tests` run produces, in `voiceguard/e2e/results/`:
`appium_report.json`/`.xml` (raw pytest-json-report/JUnit),
`appium_summary.json` (parsed totals + module breakdown + failures),
`execution-report.html` (the human-readable report),
`screenshots/` (failures only). `reports/build_master_test_report.py`
(repo root) already reads `appium_report.json` generically into the
cross-discipline `VoiceGuard_App_Testing_Report.xlsx` — no changes needed
there when this suite grows.

Live report: `https://amit-0000.github.io/AMIT-KRISHNA/reports/latest/execution-report.html`
(trend view: `.../reports/trends.html`).

**One-time manual step**: GitHub Pages must be enabled once in this repo's
Settings → Pages, with source set to the `gh-pages` branch, before the first
`deploy-appium-report` run will actually serve anything (the workflow
creates/updates that branch; it can't flip the repo setting itself).

## Troubleshooting

- **"No Chromedriver found"**: the emulator's stock Chrome (109.0.5414) has
  no bundled driver matching Appium's `chromedriverAutodownload` (which only
  resolves 115+). The workflow fetches the matching legacy driver and points
  `CHROMEDRIVER_EXECUTABLE` at it — don't re-enable autodownload.
- **Instrumentation launch timeout**: expected under CI's CPU contention;
  timeouts are already set to 300s. If you see failures well past that,
  it's a new issue, not the known one.
- **A GuestGuard-page test unexpectedly redirects to `/dashboard`**: it's
  using plain `driver` instead of `unauthenticated_driver` — see "Fixture
  design" above.
- **appium-tests is red**: it's a real failure now — no continue-on-error
  is masking it. Check the job's own "Appium Mobile Web Test Summary" step
  summary first (pass rate vs. `APPIUM_MIN_PASS_RATE`), then
  `execution-report.html` in the `appium-report` artifact (or the Pages URL)
  for which specific tests failed and why, before assuming it's emulator
  infra rather than a real regression.
