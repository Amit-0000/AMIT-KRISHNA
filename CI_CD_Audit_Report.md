# CI/CD Audit Report

Date: 2026-08-06
Scope: `.github/workflows/backend.yml`, `docker.yml`, `frontend.yml`, `qa-suite.yml`

## Workflow map

| Workflow | Trigger paths | Jobs | Depends on |
|---|---|---|---|
| `backend.yml` | `voiceguard/api/**`, `voiceguard/src/**`, `pyproject.toml`, `requirements*.txt` | `lint` (ruff, report-only), `test` (pytest + coverage) | none — self-contained, bare Python |
| `docker.yml` | same backend paths + `Dockerfile` | `build` (docker buildx build of `api/Dockerfile.ml`, no push) | none |
| `frontend.yml` | `voiceguard/frontend/**` | `build` (npm ci, eslint, tsc, vite build) | none |
| `qa-suite.yml` | any push/PR to `main` | `unit-tests`, `vulnerability-dast`, `load-test`, `selenium-web`, `appium-mobile-web` (continue-on-error), `build-report` (needs all 5, `if: always()`) | `build-report` downloads artifacts from the other 5 jobs |

No workflow requires a GitHub Secret — see **Secrets audit** below.

## Issues found and fixed

### 1. `vulnerability-dast` — `ModuleNotFoundError: No module named 'jwt'`
(Fixed in a prior session, confirmed still green here.) `automated_test/01_authn_bypass.py` imports `jwt` but the job only installed `requests`. Fix: `automated_test/requirements.txt` (requests, pyjwt) + `pip install -r requirements.txt`.

### 2. `load-test` — k6 exit 255, two independent root causes
- `baseline_load_test.js`'s `handleSummary()` hardcoded `/scripts` was never mounted as `/results` — wrong path, "no such file or directory".
- `grafana/k6` runs as a non-root user by default; writing into the runner-owned bind mount at `/scripts` failed with "permission denied", confirmed against real CI logs (not reproducible on this Windows dev box, where Docker Desktop bind mounts don't enforce POSIX UID checks the same way).
- **Fix:** `handleSummary()` now writes to `/scripts/summary_new.json`; the now-redundant `--summary-export` CLI flag was dropped (k6 ignores it when `handleSummary` is defined — verified locally); `docker run` now passes `--user "$(id -u):$(id -g)"`.

### 3. `load-test` — every scan upload returned 409, tripping the 5% error threshold
Root cause: `sample.wav` is byte-identical on every upload. The backend has a genuine per-user duplicate-content rejection feature (`api/scans/service.py:215`, `find_active_duplicate`). The k6 script attempts up to 5 uploads/VU with identical bytes, so uploads 2–5 always legitimately 409. This is a **test-script bug**, not an app bug — the DAST suite (`automated_test/lib/fixtures.py`) already solved the identical problem by perturbing one PCM sample per generated file.
**Fix:** `uniqueWavBytes()` perturbs the first 16-bit PCM sample (byte offset 44) with a value derived from `Date.now()`/`__VU`/`__ITER` before every upload. Verified locally end-to-end against a fresh stack: 475/475 uploads succeeded, 0% `http_req_failed`.

### 4. `load-test` — `build_excel.py` needs `openpyxl`, never installed
The job had no Python setup or dependency-install step at all; it only worked on a dev machine that happened to have `openpyxl` installed globally. **Fix:** new `voiceguard/performance/requirements.txt` (`openpyxl==3.1.5`) + `actions/setup-python` + `pip install -r`.

### 5. `appium-mobile-web` — three layered issues, traced one real CI run at a time

**5a. `ERROR: file or directory not found: \`, exit code 4 — fixed and confirmed.**
The `reactivecircus/android-emulator-runner`'s `script:` input is **not** executed as one script — its `script-parser.ts` splits the block on newlines and runs each line as an independent `sh -c` invocation (confirmed by reading the actual action source, and by two separate `[command] /usr/bin/sh -c ...` lines in the real CI log). The `cd` on one line and the `\`-continued `pytest` command on the next line don't share shell state; the backslash was interpreted as a literal argument by the isolated single-line invocation.
**Fix:** collapsed to one self-contained line: `cd "..." && python -m pytest ...`. Re-ran on real CI: pytest now collects and executes all 5 tests (previously "collected 0 items") — confirms this specific bug is fully resolved.

**5b. `adb install ... timed out after 20000ms` / `instrumentation process cannot be initialized within 30000ms` — attempted, inconclusive.**
Fixing 5a let the suite actually run, which surfaced this next layer: `adb`/UiAutomator2-server default timeouts (20s/20s/30s) were too tight for a cold GitHub-hosted emulator. Error messages named the exact capabilities to raise.
**Fix attempted:** `adb_exec_timeout`, `uiautomator2_server_install_timeout`, `uiautomator2_server_launch_timeout` all raised to 120s in `voiceguard/e2e/appium/conftest.py`. Re-ran on real CI: the failure mode changed (job ran 33min vs 23min, further before failing) but did not resolve — this ruled out "just needs more time" as the root cause and surfaced 5c.

**5c. `No Chromedriver found that can automate Chrome '109.0.5414'` — attempted, did not resolve; root-caused as infrastructure.**
The `api-level 33` / `google_apis` emulator image ships a stock Chrome (109.0.5414, ~Jan 2023) with no bundled matching chromedriver. Appium's own error text names the workaround.
**Fix attempted:** `chromedriverAutodownload: true` capability added. Re-ran on real CI: job duration climbed again (39m47s), and it failed at the *same* "instrumentation process cannot be initialized within 120000ms" point as 5b, now preceded by ~40 seconds of repeated `adb ... failed with exit code 1`.

**Final diagnosis:** three real, independently-confirmed root causes were found by reading actual failing CI logs after each fix (never guessed) — 5a is fully fixed. 5b/5c are consistent with the GitHub-hosted emulator's UiAutomator2 instrumentation process being unable to reliably launch under this runner's resource constraints (nested-KVM Android emulation is a known-tight fit on shared runners), not a bug in this repo's workflow, test code, or application. Escalating timeouts made the job take longer without changing the outcome — a signal that no further client-side tuning was going to fix this without different infrastructure (a self-hosted runner, or an emulator image/API-level combination not available via `reactivecircus/android-emulator-runner` on `ubuntu-latest`). Stopped here per the explicit instruction to avoid guessing and to document rather than blindly iterate once the evidence pointed to infrastructure rather than a fixable script/config bug.

### 6. Reproducibility: ad-hoc single-package installs
Per the "don't install packages one-by-one" directive, consolidated every bare `pip install <pkg>` into a versioned requirements file:
- `automated_test/requirements.txt` — `requests`, `pyjwt==2.10.1` (also now reused by `selenium-web`/`appium-mobile-web`'s fixture-provisioning steps, which previously ran their own unpinned `pip install requests` *before* `actions/setup-python` even executed).
- `voiceguard/performance/requirements.txt` — `openpyxl==3.1.5`.
- `voiceguard/reports/requirements.txt` — `openpyxl==3.1.5` (replaces `build-report`'s unpinned `pip install openpyxl`).
- `coverage` and `pytest-json-report` were unpinned ad-hoc installs in `backend.yml`/`qa-suite.yml`; moved into `voiceguard/api/requirements.txt` (pinned `coverage==7.6.10`, `pytest-json-report==1.5.0`), matching the repo's existing convention of keeping test tooling alongside `pytest`/`pytest-asyncio` in that file.

### 7. Backend startup health-gating (Phase 5) — already compliant, verified not assumed
All three `Wait for ... health` steps already poll (`for i in $(seq 1 60); curl ...; sleep 2; done`) — no fixed sleeps anywhere. Traced the dependency chain to confirm a 200 from `/health` really does mean Postgres + Redis + backend + ML runtime are all ready:
- `docker-compose.yml`'s `backend` service has `depends_on: {postgres: condition: service_healthy, redis: condition: service_healthy}`.
- `api/Dockerfile.ml`'s `CMD` is `alembic upgrade head && uvicorn ...` — migrations run and must succeed before the server even starts.
- `api/main.py`'s startup event loads the ML model synchronously; log ordering confirms `"ML model loaded on cpu"` always precedes `"Application startup complete"`.

No changes needed here.

## Deprecated GitHub Actions — upgraded

Checked live via GitHub's API (not assumed) which major version introduced Node 24 (`runs.using`) for each action, and read each major's release notes for breaking changes relevant to this repo's actual usage before bumping:

| Action | Before | After | Why safe |
|---|---|---|---|
| `actions/checkout` | v4 | v7 | Node24 runtime only; no input changes used here |
| `actions/setup-python` | v5 | v7 | v7 removes `pip-install` input — unused in this repo |
| `actions/setup-node` | v4 | v7 | v5/v6 breaking changes are about auto-detected caching; we always pass explicit `cache: npm` |
| `actions/upload-artifact` | v4 | v7 | Node24 runtime + opt-in `archive: false` feature, unused |
| `actions/download-artifact` | v4 | v8 | v5's breaking change only affects single-artifact-by-ID downloads; this repo always does "download all" (`path: artifacts`, no `name`/`artifact-ids`), which is unaffected |
| `docker/setup-buildx-action` | v3 | v4 | Node24 runtime; removed inputs are ones this repo doesn't set |
| `docker/build-push-action` | v6 | v7 | Node24 runtime; removed env vars this repo doesn't set |
| `reactivecircus/android-emulator-runner` | `@v2` | `@v2` (unchanged) | Already a floating major tag resolving to v2.38.0, already `node24` |

Also added `concurrency: {group: "${{ github.workflow }}-${{ github.ref }}", cancel-in-progress: true}` to all four workflows.

## Secrets audit

`grep -rn "secrets\." .github/workflows/*.yml` returns **zero matches**. No workflow references any GitHub Secret.

- **Required:** none.
- **Optional:** none.
- **Missing:** none — nothing is failing due to a missing secret. All credentials used in CI are dev/test values from the checked-in `voiceguard/api/.env.example` (already flagged and accepted as a known false positive by `automated_test/08_hardcoded_creds.py`'s own scan).

## Verification performed (real commands, not assumed)

- `automated_test/01_authn_bypass.py` run standalone: no `ModuleNotFoundError`, 81 checks, 0 findings.
- Full `automated_test/run_all.py`: 231 checks, **0 findings**.
- k6 `baseline_load_test.js` run against a fresh (`docker compose down -v` / `up -d --build`) local stack via `docker run grafana/k6:latest` with the fixed workflow command: exit 0, 4919 requests, **0% `http_req_failed`**, 475/475 scan uploads returned 201.
- `performance/parse_results.py` and `performance/build_excel.py` run against the real k6 output: valid `.xlsx` produced.
- Selenium suite run against a live stack (Chrome + Selenium Manager, matching CI's headless setup): **12/12 passed**.
- Backend unit tests run inside a real `python:3.12-slim` container (matching CI's pinned Python version exactly, since this dev machine only has 3.12 unavailable natively): **191/191 passed**.
- Frontend `npm ci && npm run lint && npx tsc -b --noEmit && npm run build`: clean (3 pre-existing lint warnings, 0 errors; build succeeds).
- `voiceguard/reports/build_master_test_report.py` run against all real locally-generated artifacts: produced a valid `.xlsx` with all 7 expected sheets populated (Appium sheet correctly empty/graceful since no `appium_report.json` exists locally — no Android SDK on this machine).
- All 4 workflow YAML files parsed successfully with `yaml.safe_load` after every edit.
- Appium's `android-emulator-runner` script-splitting root cause confirmed against the action's actual `script-parser.ts` source (not guessed), and against the real failing CI log showing two separate `sh -c` invocations.

**Real GitHub Actions confirmation (not just local reproduction):** pushed 3 commits and watched each real CI run to completion:
1. `40434c7` ("ci: stabilize GitHub Actions workflows") — **Backend, Docker, Frontend all green**; **QA Suite green** (`unit-tests`, `vulnerability-dast`, `load-test`, `selenium-web`, `build-report` all passed for real on `ubuntu-latest`; `appium-mobile-web` failed at 5a, non-blocking via its pre-existing `continue-on-error`).
2. `26c9b23` (Appium timeout fix) — confirmed 5a is fully fixed (pytest collects/runs); surfaced 5b→5c.
3. `a28cd11` (chromedriverAutodownload fix) — confirmed 5c does not resolve the instrumentation-launch failure; diagnosis finalized as infrastructure.

## Remaining limitations

- **Appium job** — see §5 above for the full three-layer investigation. 5a (the actual workflow bug) is fixed and confirmed on real CI. 5b/5c are consistent with a genuine GitHub-hosted-runner resource/emulator-instrumentation limitation, not a bug in this repo. It already carries the pre-existing `continue-on-error: true` (not added by this pass — already present, with its own honest "non-blocking until proven green" comment anticipating exactly this), so it cannot fail the overall workflow, and its failure is visible (not hidden) in the job's own red status.
- **Duplicate Docker builds**: `docker.yml` and each of `qa-suite.yml`'s `vulnerability-dast`/`load-test`/`selenium-web`/`appium-mobile-web` jobs independently rebuild the same `voiceguard-backend` image on isolated runners with no shared layer cache — `docker.yml` uses `cache-from/cache-to: type=gha` via `buildx`, but `docker compose up -d --build` in `qa-suite.yml` doesn't wire into that cache backend. Fixing this would require a registry- or GHA-cache-backed shared image build published from one job and pulled by the others — an architectural change with enough surface area (registry auth, tagging, cross-job coordination) that it wasn't attempted here to keep this pass low-risk and fully verified. Documented as a follow-up optimization, not attempted.
- `backend.yml`'s `lint` job runs `ruff check . || true` (report-only, non-blocking) — this is pre-existing, deliberate ("no lint baseline established yet" per its own comment), left unchanged.

## Addendum — 2026-08-07 follow-up pass

Re-ran this audit end-to-end (Docker Desktop, `gh run list`/`gh run view`) rather than trusting the report above at face value. Findings:

- All 4 workflows were already green on real CI from the prior pass (`gh run list` showed `40434c7`/`26c9b23`/`a28cd11`/`323736f` all `success`, Appium sub-job red-but-`continue-on-error` as documented).
- Found 3 **uncommitted** working-tree edits that predated this session and were never verified or committed: `.gitignore`/`voiceguard/.gitignore` additions (Office lock files, CI-generated `security/`/coverage output — confirmed via `git ls-files` that nothing currently tracked matches these patterns, so no accidental un-tracking), and `voiceguard/docker-compose.yml`'s frontend dev/E2E image bumped `node:20-alpine` → `node:22-alpine`.
- Verified the Node bump was warranted, not cosmetic: Node 20 passed upstream end-of-life in April 2026 (this session runs 2026-08-07), i.e. an actually-deprecated runtime per Phase 12's mandate, not merely a hypothetical.
- Verified locally before committing: `docker compose up -d --build postgres redis backend frontend` with the new image — backend `/health` 200, frontend Vite dev server 200, clean logs, no ABI/native-binding issues from the fresh `node_modules` volume. Then ran the frontend's exact CI steps (`npm ci && npm run lint && npx tsc -b --noEmit && npm run build`) inside `node:22-alpine` directly — identical result to Node 20 (0 lint errors, same 3 pre-existing `react-refresh` warnings, clean build).
- Extended the fix for consistency: `frontend.yml`'s `actions/setup-node` was still pinned to Node 20 (the CI build runtime, independent of the docker-compose dev/E2E image) — bumped to `"22"` to match.
- Committed (`3554e0d`) and **pushed to real CI** to verify rather than assume:
  - `Frontend` workflow (run `31184267711`): green, 37s, `npm ci`/lint/tsc/build all passed on Node 22.
  - `QA Suite` workflow (run `31184267483`): green overall. `Selenium (Web E2E)` passed in 4m1s against the now-`node:22-alpine` frontend container (this is the job that actually exercises that image, since `backend.yml`/`docker.yml` don't touch it). `Unit tests`, `Vulnerability/DAST`, `Load test (k6)`, `Build consolidated Excel report` all passed. `Appium` failed at the identical previously-documented point (`Run Appium mobile-web suite on Android emulator`, ~19m37s) — same infrastructure limitation as §5c above, still non-blocking via its pre-existing `continue-on-error`, still visible (not hidden) as a red sub-job.
- Removed a stray `voiceguard/frontend/nul` file created as an accidental byproduct of a Windows/Git-Bash `curl -o /dev/null` redirect during this session's local verification — never committed.

No regressions introduced. No new root causes found. Repository state: all 4 workflows pass on real GitHub Actions; the one known-and-documented Appium infrastructure limitation is unchanged and non-blocking.
