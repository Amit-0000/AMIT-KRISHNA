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

### 5. `appium-mobile-web` — `ERROR: file or directory not found: \`, exit code 4
The `reactivecircus/android-emulator-runner`'s `script:` input is **not** executed as one script — its `script-parser.ts` splits the block on newlines and runs each line as an independent `sh -c` invocation (confirmed by reading the actual action source, and by two separate `[command] /usr/bin/sh -c ...` lines in the real CI log). The `cd` on one line and the `\`-continued `pytest` command on the next line don't share shell state; the backslash was interpreted as a literal argument by the isolated single-line invocation.
**Fix:** collapsed to one self-contained line: `cd "..." && python -m pytest ...`. Everything upstream of this step (SDK/emulator boot, Appium server) already worked in CI — this was purely a workflow-scripting bug.

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

## Remaining limitations

- **Appium job** could not be run end-to-end locally (no Android SDK on this dev machine — the suite's own docs already state it's CI-only). The fix is grounded in the action's real source code and the actual CI failure log, but the *actual* Android-emulator run of this specific fix has not yet been observed in CI as of report time. It already carries the pre-existing `continue-on-error: true` (a job-level infrastructure allowance, not something added to hide the fix), so it cannot fail the overall workflow even if some other emulator-specific issue surfaces.
- **Duplicate Docker builds**: `docker.yml` and each of `qa-suite.yml`'s `vulnerability-dast`/`load-test`/`selenium-web`/`appium-mobile-web` jobs independently rebuild the same `voiceguard-backend` image on isolated runners with no shared layer cache — `docker.yml` uses `cache-from/cache-to: type=gha` via `buildx`, but `docker compose up -d --build` in `qa-suite.yml` doesn't wire into that cache backend. Fixing this would require a registry- or GHA-cache-backed shared image build published from one job and pulled by the others — an architectural change with enough surface area (registry auth, tagging, cross-job coordination) that it wasn't attempted here to keep this pass low-risk and fully verified. Documented as a follow-up optimization, not attempted.
- `backend.yml`'s `lint` job runs `ruff check . || true` (report-only, non-blocking) — this is pre-existing, deliberate ("no lint baseline established yet" per its own comment), left unchanged.
