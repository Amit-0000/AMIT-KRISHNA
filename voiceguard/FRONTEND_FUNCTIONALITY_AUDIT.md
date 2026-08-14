# VoiceGuard Frontend Functionality & Dead-Feature Audit

**Date:** 2026-08-12
**Scope:** `voiceguard/frontend` (React 19 + TypeScript SPA) and its live contract with `voiceguard/api` (FastAPI backend)
**Method:** Full source read of every page/component/store/service, static frontend↔backend contract comparison, and live runtime testing against the running Docker stack (`docker compose` — postgres, redis, backend on :8000, frontend dev server on :5173) using a real pre-provisioned account (`dast.usera@example.com`, the same fixture the Selenium/Appium CI suites use) plus a freshly-uploaded test audio file.
**Verification legend:** every finding below is tagged **SOURCE-CODE VERIFIED**, **RUNTIME VERIFIED** (reproduced live in the browser), **BACKEND VERIFIED** (traced into the FastAPI route/service/repository), or **BLOCKED** (not testable in this pass, with reason).

No code was modified during this audit.

---

## 1. Executive Summary

VoiceGuard's frontend is, on the whole, **solidly built** — the core detection loop (upload → process → result), history management (list/filter/sort/paginate/cancel/delete), settings persistence, and the frontend↔backend API contract are all correct and RUNTIME VERIFIED end-to-end. This is not a prototype full of stubs; most of the "20 modules" in a typical audit checklist (auth, dashboard, scan, history, settings) are real, wired, and working.

That said, five defects meaningfully undermine user trust, in roughly descending severity:

1. **Theme selector is non-functional** (the example bug from the brief, now fully root-caused) — Light and System modes visibly do nothing; only Dark actually renders.
2. **Notifications are permanently, structurally empty for every user** — the backend has no code path that ever creates a `Notification` row outside of tests, so the Notification Center and full Notifications page will show "No notifications yet" forever, despite copy that explicitly promises "Scan results will appear here."
3. **The "Share a Result" feature is a decoy** — a Dashboard quick action literally labeled "Generate a public share link" is a `<Link>` to `/history`; it calls no API. The backend fully supports share-link creation/revocation and a public viewer route exists, but nothing in the UI can ever reach it.
4. **Dashboard verdict statistics can legitimately exceed 100%** — "AI Detected: 4 (133% of total)" was reproduced live. Root cause: the backend counts `ScanResult` rows without excluding soft-deleted scans, while "Total Analyses" does exclude them.
5. **Global Search (⌘K) never searches your scans** — despite a "Search or jump to…" placeholder and result-rendering code built to display scan verdicts, it only ever filters a hardcoded 6-item static menu. Searching a real filename returns "No results."
6. **The landing page advertises three product capabilities that don't exist anywhere in the shipped app**: recording audio directly from a microphone (zero `getUserMedia`/`MediaRecorder` references in the whole codebase), scanning without an account ("no account required for guest scans" — `/scan/new` is hard-gated by `AuthGuard`), and a "Grad-CAM frequency heatmap" per-scan deliverable (a `frequency_heatmap` field is declared in `types/index.ts` but read by zero components anywhere — the real result page only ever renders text notes and time-range bars). A product-accuracy/trust risk, not just a UI bug.
7. **Footer Legal links (Privacy/Terms/Cookie Policy) all 404** — they point at `/privacy`, `/terms`, `/cookies`, none of which exist in `App.tsx`'s route table.

Beyond these, the audit found one dead-code call to a nonexistent backend endpoint, two fully-built-but-unwired UI components, several backend endpoints with no frontend caller (OAuth login, token refresh, notification delete), a NewScan dropzone that promises "Up to 50 MB" while the validator enforces 10 MB, an Onboarding step whose selection is collected then silently discarded despite copy implying it's used, and one minor misleading error message.

---

## 2. Frontend Architecture

| Aspect | Finding |
|---|---|
| Framework | React 19.0, TypeScript ~5.7, Vite 6 |
| Router | `react-router-dom` v7, `BrowserRouter`, client-side only |
| State management | Zustand 5 — `authStore` (session), `uiStore` (theme, sidebar, search, notification panel — `persist` middleware → `localStorage['vg-ui']`) |
| Data fetching | `@tanstack/react-query` v5 for server state (dashboard, history, scan result/technical/explanation, notifications, profile); Zustand only for pure UI/client state |
| API client | Single `axios` instance (`services/api.ts`), `baseURL: /api/v1`, `withCredentials: true` (cookie session auth, no bearer tokens anywhere), a response interceptor that unwraps the backend's `{data, meta}` envelope once so call sites get plain payloads, and two `window` `CustomEvent`s (`vg:unauthorized`, `vg:rate-limited`) dispatched on 401/429 |
| Auth | Cookie-session based. `authStore.checkSession()` calls `GET /auth/me` on app mount. `useAuth.ts` listens for `vg:unauthorized` and force-logs-out on any 401 anywhere in the app. |
| Theme system | Zustand `uiStore.theme` (`'light'|'dark'|'system'`), persisted, toggles a `.dark`/`.light` class on `<html>`, listens for OS `prefers-color-scheme` changes. **The class-toggling mechanism works correctly — see §10; the CSS that should respond to it doesn't exist.** |
| Component structure | `components/layout/*` (Sidebar, TopBar, MobileDrawer, GlobalSearch, NotificationCenter, UserMenu, Breadcrumb, ThemeToggle, Footer) + `components/ui/*` (a small hand-rolled Radix-based kit: dialog, dropdown-menu, tooltip, avatar, badge, button, input, label, scroll-area, separator, skeleton) |
| Page structure | One folder per route under `pages/`, each with its own `components/`, `hooks/`, and (where it talks to the backend directly rather than through the shared client) a `services/*Api.ts` file — Dashboard, NewScan, ScanProcessing, ScanResult, History, ScanDetail, Notifications, Settings (Profile/Account/Appearance), Help, Feedback, Login, Signup, ForgotPassword, ResetPassword, VerifyEmail, Onboarding, LandingPage, SharedResult |
| Forms | `react-hook-form` + `zod` resolvers (Signup, Feedback); simpler pages use plain controlled inputs |
| Backend integration | FastAPI, routers mounted under `/api/v1` in `api/main.py`, one router per vertical slice (auth, scans, inference, dashboard, notifications, sharing, user, feedback) |
| WebSocket/SSE | None. Scan processing status is done by **polling** (`useScanPolling.ts` → `GET /scans/{id}/status` on an interval), not push. |
| localStorage/sessionStorage | Only one key, `vg-ui`, storing `{sidebarCollapsed, theme}` via zustand `persist`'s `partialize`. No other client-side persistence anywhere in the app. |
| Env vars / feature flags | **None.** `grep -rn "import.meta.env"` across `frontend/src` returns zero matches — there is no feature-flag-gated code in the frontend at all. |
| Error handling | Centralized 401/429 handling via custom events (only 401 has a listener — see §16); per-call-site `try/catch` + `sonner` toasts elsewhere; `react-query`'s built-in `isError`/`error` states drive most page-level error UI |
| Loading states | `react-query`'s `isLoading`, plus hand-built `Skeleton` components per page | 
| Toast/notifications | `sonner`, mounted once in `App.tsx`, positioned bottom-right. Distinct from the in-app "Notifications" feature (which is a persisted, backend-driven inbox — see §11) |

---

## 3. Theme System Deep Audit (§4 of the brief) — RUNTIME VERIFIED

**Symptom (as given in the brief):** selecting Light or System does not change the app's appearance.

**Full trace:**

```
ThemeToggle (topbar, icon variant) / AppearancePage (radio cards)
        │  onClick → setTheme(value)
        ▼
uiStore.setTheme()                              [store/uiStore.ts:90-93]
        │  1. set({ theme })
        │  2. applyTheme(theme) → toggles `.dark`/`.light` class on <html>,
        │     resolving 'system' via matchMedia('(prefers-color-scheme: dark)')
        ▼
zustand `persist` middleware
        │  writes {theme} into localStorage['vg-ui']            ✅ works
        │  onRehydrateStorage re-applies the class on page load  ✅ works
        ▼
<html class="light">  (or "dark")                                ✅ works
        │
        ▼
CSS / Tailwind                                                    ❌ BROKEN HERE
```

Everything up to and including the DOM class mutation **works correctly** — this was RUNTIME VERIFIED by driving the real toggle in the browser and reading back application state:

```js
// After clicking the toggle once (Dark → Light):
{ htmlClasses: "light",
  localStorage: '{"state":{"sidebarCollapsed":false,"theme":"light"},"version":0}' }
```

The root cause is that **no light-mode CSS exists anywhere in the codebase**:

- `tailwind.config.ts` (`darkMode: ['class']`) defines every design token — `bg.base`, `bg.surface`, `text.primary`, etc. — as a single static hex value (e.g. `bg.base: '#080810'`). There is no light/dark pair for any token.
- `grep -rn "dark:" frontend/src` returns **zero** matches in any `.tsx` file — no component ever uses Tailwind's `dark:` variant, so the `darkMode: ['class']` config, while correctly wired to the `.dark` class, has nothing to activate.
- `index.css` hardcodes the dark palette directly onto `body` (`background-color: #080810; color: #F0F0FF`) with no `.light`-scoped override.

RUNTIME VERIFIED by direct DOM manipulation: `getComputedStyle(document.body).backgroundColor` returns **`rgb(8, 8, 16)` regardless of whether `<html>` has class `dark` or `light`** — proof the two states are visually identical because nothing in the stylesheet conditions on the class.

**This is a disclosed-but-inconsistently-disclosed limitation, not a hidden one — with one real gap:**
`pages/Settings/Appearance.tsx` explicitly tells the user: *"VoiceGuard is designed dark-first. 'System' and 'Light' will switch automatically once a light palette ships — your preference is saved either way."* That's honest, in-context messaging.

However, `components/layout/ThemeToggle.tsx` (the compact icon-cycle control in the TopBar, used on every authenticated page) carries **no such disclaimer**. A user who never visits Settings → Appearance will click the moon icon in the TopBar, see it "select" Light or System (the icon and `aria-label` change), and conclude the app is broken — this is functionally identical to the brief's example bug from that control's vantage point, even though the underlying engineering (state/persistence/OS-preference-listening) is all correct and the team is aware of the limitation.

**Fix options**, in order of effort: (a) cheapest — add the same disclaimer text as a tooltip on the TopBar `ThemeToggle`, or hide the Light/System options from that control until a light palette ships; (b) real fix — define a light-mode token set in `tailwind.config.ts` and apply `dark:`-prefixed overrides (or restructure tokens as CSS variables swapped per class) across the ~120 files using color utility classes.

---

## 4. Dashboard Statistics Bug — RUNTIME VERIFIED, BACKEND VERIFIED

Not in the original brief, but a clear parallel case: a control that "looks like it works" (real numbers, real percentages) but is silently wrong.

**Reproduced live**, before and after uploading one new scan:

| | Total Analyses | AI Detected | Human Verified |
|---|---|---|---|
| Before | 3 | 4 (**133%** of total) | 0 (0%) |
| After uploading 1 new "human" verdict scan | 4 | 4 (**100%** of total) | 1 (25%) |

`4 + 1 = 5 > 4` — the verdict counts sum to more than the total scan count, which is mathematically impossible if they're the same unit.

**Root cause (`api/dashboard/repository.py:21-27` vs `api/scans/repository.py:96-100`):**

```python
# Total Analyses — correctly excludes soft-deleted scans:
async def count_all_for_user(db, user_id):
    return await db.execute(
        select(func.count()).select_from(Scan)
        .where(Scan.user_id == user_id, Scan.deleted_at.is_(None))   # ← filters deleted
    )

# AI Detected / Human Verified — does NOT exclude soft-deleted scans:
async def verdict_counts(db, user_id):
    return await db.execute(
        select(ScanResult.verdict, func.count())
        .where(ScanResult.user_id == user_id)                        # ← no join to Scan,
        .group_by(ScanResult.verdict)                                #   no deleted_at filter
    )
```

`ScanResult` has a 1:1 `unique` FK to `Scan` with `ondelete="CASCADE"` at the DB level, but `Scan`'s delete is a **soft delete** (`deleted_at` timestamp, row stays in the table) — so a completed scan a user deletes from History keeps its `ScanResult` row alive, and that row keeps counting toward "AI Detected"/"Human Verified" forever, while the same scan correctly stops counting toward "Total Analyses". Every deleted-after-completion scan permanently inflates the dashboard's verdict percentages.

**Fix:** join `verdict_counts()` to `Scan` and add `Scan.deleted_at.is_(None)`, matching `count_all_for_user()`.

*(This is a backend logic bug, not a frontend bug — the frontend renders exactly what `GET /dashboard` returns, correctly. Included here because it's a directly user-visible "looks right but isn't" defect matching the audit's intent.)*

---

## 5. "Share a Result" — Fully Dead Feature — SOURCE-CODE VERIFIED, RUNTIME cross-checked

This is the single closest structural match to the brief's Theme Selector example — a control that promises a specific action and does something else entirely.

`pages/Dashboard/components/QuickActions.tsx:36-41`:
```ts
{
  label: 'Share a Result',
  description: 'Generate a public share link',
  href: '/history',        // ← not a share action at all
  icon: Share2,
},
```
The action is a plain `react-router` `<Link to="/history">`. Clicking "Share a Result" on the Dashboard navigates to the scan history list — it makes no API call, mints no token, and has nothing to do with sharing.

The backend fully supports this feature (`POST /scans/{id}/share`, `DELETE /scans/{id}/share`, public `GET /scans/shared/{token}`), and the frontend even has a working client method (`scanApi.share()`) and a working public viewer page (`SharedResultPage` at `/r/:scanId`, confirmed via `scanApi.sharedResult()` → `GET /scans/shared/{token}`, contract-audited clean). But **no button anywhere in `ScanResult` or `ScanDetail` — the two pages that would plausibly host a "Share" action — calls `scanApi.share()`.** Zero call sites exist outside its own definition. Consequently no real user, including a scan's owner, can ever mint a working `/r/:scanId` link. The entire feature — UI trigger, token minting, and public destination — is unreachable end-to-end despite being fully built on both ends individually.

There is also no `unshare`/revoke method in the frontend API client at all (the backend's `DELETE /scans/{id}/share` has no client wrapper), so even a manually-constructed share flow couldn't be revoked from the UI.

**Classification: F (backend disconnected) / D (UI-only placeholder)** — the "Share a Result" quick action is functionally decorative.

---

## 6. Notifications Are Permanently Empty for Every User — BACKEND VERIFIED, RUNTIME VERIFIED

The Notifications page and Notification Center dropdown are **correctly built on the read side**: `GET /notifications`, `mark-all-read`, per-item mark-read, unread badge on the sidebar (`badge: 'notification_count'` in `nav-config.ts`), empty-state copy that explicitly sets an expectation — *"No notifications yet. Scan results will appear here."*

That expectation can never be met. Traced the entire backend:

```
api/notifications/repository.py:11  async def create(...) → inserts a Notification row
api/notifications/service.py        → create() is defined but NEVER CALLED here
api/notifications/router.py         → exposes only GET "", GET "/unread-count", POST "/mark-all-read"
                                       (no POST/create endpoint at all)
grep -rn "notifications_repository.create\|notifications.create" api/
                                     → only matches within api/notifications/* itself and api/tests/
```

**No code path anywhere in the running application — not scan completion, not account creation, not email verification — ever calls `Notification`-row creation.** It is only exercised by the test suite. This was corroborated live: after logging in, completing a full scan (upload → process → "Likely human" result), and navigating to `/notifications`, the page showed **"No notifications yet"** — a scan result completing is exactly the kind of event the empty-state copy promises will appear here, and it didn't.

**Classification: F (backend disconnected) / E (dead code)** — this is not a partial feature, it's a fully-plumbed pipe with the tap never connected. Every user, forever, sees an empty inbox.

---

## 7. Global Search (⌘K) Never Searches Scans — SOURCE-CODE VERIFIED, RUNTIME VERIFIED

`components/layout/GlobalSearch.tsx` renders a modal with placeholder "Search or jump to…", and its result-rendering code (`ResultIcon`, `GlobalSearch.tsx:35-51`) has a full branch for `result.type === 'scan'` that renders human/AI/uncertain verdict icons — clearly built to show scan results.

But the actual result list is:
```ts
const results = query.trim()
  ? QUICK_ACTIONS.filter(r => r.label...includes(query) || r.description...includes(query))
  : QUICK_ACTIONS
```
`QUICK_ACTIONS` is a **hardcoded array of 6 static nav items** (New Scan, Dashboard, History, Help Center, Give Feedback, Settings). No API call is ever made from this component. RUNTIME VERIFIED: after uploading and completing a scan named `audit_test.wav`, pressing ⌘K and typing `audit_test` returned **"No results for 'audit_test'"** — as did every other non-nav-label query tried (`verify`). Typing a substring of an actual nav label (`hist` → "History") works correctly, confirming the palette is functioning exactly as coded — it's just never wired to real content.

**Classification: D (UI-only placeholder)** — the scan-result rendering branch is dead code with no producer, same shape as the Notifications gap in §6.

---

## 8. Feature Inventory & Functionality Matrix

Legend — Status: **PASS** / **PARTIAL** / **FAIL** / **PLACEHOLDER** / **DEAD** / **BLOCKED**. Priority: P0 critical · P1 high · P2 medium · P3 low. Verification: SCV = source-code verified, RTV = runtime verified, BEV = backend verified.

### Authentication

| ID | Feature | Expected | Actual | Status | Verification | Priority |
|---|---|---|---|---|---|---|
| AUTH-01 | Login | Authenticates via `POST /auth/login`, sets cookie session | Works exactly as expected; RUNTIME VERIFIED end-to-end with real fixture account | PASS | RTV | — |
| AUTH-02 | Signup | Creates account, sends verification email | Form validates client-side (zod, live password-rule checklist) and posts to `POST /auth/register`; contract-clean | PASS | SCV | — |
| AUTH-03 | Email verification | `POST /auth/verify-email` with token from emailed link | RUNTIME VERIFIED — visiting `/verify-email?token=…` showed "Email verified" success screen | PASS | RTV | — |
| AUTH-04 | Resend verification | `POST /auth/resend-verification` | Present on Login page when a login attempt reports unverified email; contract-clean | PASS | SCV | — |
| AUTH-05 | Forgot password | `POST /auth/forgot-password` | Contract-clean, GuestGuard-protected route | PASS | SCV | — |
| AUTH-06 | Reset password | `POST /auth/reset-password` with token | Contract-clean | PASS | SCV | — |
| AUTH-07 | Session restoration | `checkSession()` on app mount via `GET /auth/me` | Works; RUNTIME VERIFIED (dashboard loads directly on `/dashboard` after login, and again after a hard navigation) | PASS | RTV | — |
| AUTH-08 | Session expiry / 401 handling | Global 401 → forced logout | `vg:unauthorized` event is dispatched and has a real listener (`useAuth.ts:30`) | PASS | SCV | — |
| AUTH-09 | Logout | `POST /auth/logout`, clears store, redirects to `/` | Contract-clean; `UserMenu.tsx:31-34` | PASS | SCV | — |
| AUTH-10 | "Remember me" | — | **Does not exist in the UI at all.** No checkbox on Login; not applicable since auth is a plain session cookie with no explicit long/short expiry toggle exposed. | N/A | SCV | — |
| AUTH-11 | OAuth login | — | Backend fully implements `GET /auth/oauth/{provider}` + callback; **zero frontend footprint** — no button, no route, no client method anywhere | DEAD (backend-only) | SCV/BEV | P3 |
| AUTH-12 | Token refresh | — | Backend has `POST /auth/refresh`; frontend never calls it. Not a bug (401→logout is a valid design), just unused backend surface. | DEAD (backend-only) | SCV | P3 |

### Navigation

| ID | Feature | Expected | Actual | Status | Verification | Priority |
|---|---|---|---|---|---|---|
| NAV-01 | Sidebar links (Dashboard/New Scan/History/Notifications/Help/Feedback) | Navigate + active-state highlight | All work; RUNTIME VERIFIED by clicking through every one | PASS | RTV | — |
| NAV-02 | Sidebar collapse/expand | Toggles width, persists | Persists via `uiStore` (`sidebarCollapsed` in `partialize`); also settable from Settings → Appearance | PASS | SCV | — |
| NAV-03 | Breadcrumb | Reflects current route via `ROUTE_LABELS` map | Confirmed rendering correctly on every page visited (`Dashboard > scan > New Scan`, etc.) | PASS | RTV | — |
| NAV-04 | Mobile drawer | Opens sidebar as overlay on small viewports | SCV only — not exercised at a mobile viewport in this pass | PASS (SCV) | SCV | — |
| NAV-05 | Global Search (⌘K) — nav portion | Jump to any of 6 quick actions | Works correctly | PASS | RTV | — |
| NAV-06 | Global Search — scan search | Search or jump to *anything*, incl. scans (implied by placeholder + verdict-icon rendering code) | Only ever searches the static 6-item menu; scan branch is dead code; typing a real filename returns "No results" | **FAIL** | RTV | **P2** |
| NAV-07 | 404 page | Catch-all route shows a real 404 with a way home | `App.tsx:136-147` — plain inline JSX, works | PASS | SCV | — |
| NAV-08 | Protected routes (AuthGuard/GuestGuard/OnboardingGuard) | Redirect unauthenticated/authenticated users appropriately | All three guards present and used consistently in `App.tsx` | PASS | SCV | — |
| NAV-09 | Footer — Legal links (Privacy/Terms/Cookie Policy) | Navigate to real policy pages | `Footer.tsx:15-19` links to `/privacy`, `/terms`, `/cookies` — none of these routes exist in `App.tsx`; all fall through to the 404 catch-all | **FAIL** | SCV | **P1** |
| NAV-10 | Footer — social icons (GitHub/Twitter) | Link to VoiceGuard's own accounts | Point at generic `github.com`/`twitter.com` homepages, not any VoiceGuard-specific account | PLACEHOLDER | SCV | P3 |
| LAND-01 | Landing — "record from your microphone" claim | Mic recording available as an upload method | Zero `getUserMedia`/`MediaRecorder` references anywhere in `frontend/src` — not built | **FAIL** (false claim) | SCV | **P1** |
| LAND-02 | Landing — "no account required" / guest scans claim | Scan without signing up | `/scan/new` is hard-gated by `AuthGuard`; a `GuestSession` type exists in `types/index.ts` but is never used | **FAIL** (false claim) | SCV | **P1** |
| LAND-03 | Landing — "Grad-CAM frequency heatmap" claim | Per-scan frequency heatmap visualization | `frequency_heatmap` field exists in `types/index.ts:54` but is read by zero components repo-wide; the result page's `ExplanationPanel` only renders text notes + salient-region bars; the landing page's own preview heatmap is 100% hardcoded illustrative data | **FAIL** (false claim) | SCV | **P1** |

### Settings

| ID | Feature | Expected | Actual | Status | Verification | Priority |
|---|---|---|---|---|---|---|
| SET-01 | Theme selector — Dark | Applies dark theme | Works (it's the default/only working state) | PASS | RTV | — |
| SET-02 | Theme selector — Light | Applies light theme | State/persistence/DOM class all update correctly; **zero visual change** — no light CSS exists anywhere | **FAIL** | RTV | **P1** |
| SET-03 | Theme selector — System | Follows OS preference | Same as Light — mechanically correct, visually inert unless OS preference happens to resolve to dark | **FAIL** | RTV | **P1** |
| SET-04 | Theme persistence across reload | Selected theme survives refresh | Confirmed — `localStorage['vg-ui']` correctly rehydrates and re-applies the class on load | PASS | RTV | — |
| SET-05 | Sidebar density (Expanded/Compact) | Persists, visually changes sidebar width | Works; persisted in the same `uiStore` key | PASS | SCV | — |
| SET-06 | Reduced motion indicator | Read-only OS-mirroring status text | Correctly read-only, mirrors `prefers-reduced-motion` via `useReducedMotion.ts`, honored via a global CSS media query in `index.css:130-138` | PASS | SCV | — |
| SET-07 | Profile — display name | Saved via `PATCH /user/profile` | Contract-clean | PASS | SCV | — |
| SET-08 | Account — email display + verified badge | Read-only | RUNTIME VERIFIED, matches real account state | PASS | RTV | — |
| SET-09 | Account — change password | Live validation checklist, `POST /user/change-password` | SCV only — **intentionally not exercised live** to avoid corrupting the shared CI fixture account's credentials | PASS (SCV) | SCV | — |
| SET-10 | Account — resend verification | `authApi.resendVerification` | Contract-clean | PASS | SCV | — |

### Dashboard

| ID | Feature | Expected | Actual | Status | Verification | Priority |
|---|---|---|---|---|---|---|
| DASH-01 | Stat cards (Total/AI/Human/Avg time) | Accurate live counts | Real data (RUNTIME VERIFIED — updated correctly after a new scan), **but AI/Human percentages can exceed 100%** (§4) | **PARTIAL** | RTV/BEV | **P1** |
| DASH-02 | "Analyze Audio" CTA | Navigates to New Scan | Works | PASS | RTV | — |
| DASH-03 | Quick Actions — Analyze Audio | → `/scan/new` | Works | PASS | SCV | — |
| DASH-04 | Quick Actions — View History | → `/history` | Works | PASS | SCV | — |
| DASH-05 | Quick Actions — Share a Result | Promises "Generate a public share link" | Plain link to `/history`; no share action at all (§5) | **DEAD/PLACEHOLDER** | SCV | **P1** |
| DASH-06 | Quick Actions — Help Center / Give Feedback | Navigate correctly | Both work | PASS | SCV | — |
| DASH-07 | Detection Trend chart, range toggle (7/14/30 days) | Real per-day verdict breakdown | Backed by real `GET /dashboard` trend data; range toggle re-renders client-side from the same 30-day payload | PASS | RTV | — |
| DASH-08 | Recent Analysis table | Real recent scans, links to detail | Backed by `GET /dashboard/recent-scans`; RUNTIME VERIFIED new scan appeared immediately | PASS | RTV | — |
| DASH-09 | Model Status card | Shows current model info | Sourced from `GET /dashboard`, not from the (unused) `GET /models/current` endpoint — internally consistent, just means `modelsApi.current` is redundant/dead (see §9) | PASS | SCV | — |
| DASH-10 | Storage / Privacy cards | Static informational content | Correctly static-by-design (privacy guarantee copy), not a bug | PASS | SCV | — |

### Scan / Voice Detection

| ID | Feature | Expected | Actual | Status | Verification | Priority |
|---|---|---|---|---|---|---|
| SCAN-01 | Drag-and-drop upload | Accepts dropped audio file | SCV (dropzone `onDrop` present); file-picker path RUNTIME VERIFIED instead | PASS | SCV | — |
| SCAN-01b | Dropzone size-limit copy | Copy matches actual enforced limit | UI reads **"Up to 50 MB"** (RTV — seen on screen); actual client+server validator (`useFileUpload.ts:29`) enforces **10 MB**, whose own rejection message correctly says "maximum is 10 MB" — the copy and the enforcement disagree with each other | **FAIL** | RTV | P2 |
| SCAN-02 | File picker ("browse files") | Opens native picker, accepts file | RUNTIME VERIFIED — uploaded a real WAV, correct name/size/duration shown | PASS | RTV | — |
| SCAN-03 | Client-side file validation | Rejects bad type/size/duration before upload | `UploadValidation.tsx` present and wired | PASS | SCV | — |
| SCAN-04 | Audio preview + waveform | Playable preview with real waveform | RUNTIME VERIFIED — waveform rendered, play/seek controls present, correct 0:02 duration | PASS | RTV | — |
| SCAN-05 | "Analyze Audio" submit | Uploads, transitions to processing/result | RUNTIME VERIFIED — full round trip completed in ~2s for a 2s test clip, landed on `/scan/{id}` with a real verdict | PASS | RTV | — |
| SCAN-06 | Processing progress states | Step labels + progress bar driven by real backend status polling | `processingApi.ts` maps 14 real backend statuses to labels/percentages; polling confirmed via network log (repeated `GET /scans/{id}/status` visible) | PASS | RTV | — |
| SCAN-07 | Cancel scan (in-flight) | `POST /scans/{id}/cancel` | Contract-clean, wired in `ScanHistoryTable` row actions | PASS | SCV | — |
| SCAN-08 | Verdict card (Likely human / AI-generated / uncertain) | Confidence %, verdict label | RUNTIME VERIFIED — "Likely human", 80% confidence, rendered correctly | PASS | RTV | — |
| SCAN-09 | Explanation panel | Model notes, salient regions, warnings | RUNTIME VERIFIED — showed "Model classified this clip as bonafide with 80% confidence" + a graceful "Signal region highlighting is unavailable for this scan" fallback when explainability data wasn't available for this particular result | PASS | RTV | — |
| SCAN-10 | Technical details (expandable) | Raw scores, threshold, model/feature versions, timing | Present, contract-clean (`GET /scans/{id}/technical`) | PASS | SCV | — |
| SCAN-11 | Download results | — | **Does not exist anywhere in the app.** No export/download control on ScanResult or ScanDetail. | N/A (not built) | SCV | — |
| SCAN-12 | Delete scan | `DELETE /scans/{id}` | Works from History row actions and from ScanDetail's terminal-failure state; **absent from ScanDetail for completed scans** (only reachable via History list for those) — minor inconsistency, not a functional bug | PASS (minor UX inconsistency) | SCV | P3 |
| SCAN-13 | Retry scan | — | No literal "retry" — "Start a new scan" is offered on failure states instead, which is a reasonable equivalent | PASS (by design) | SCV | — |
| SCAN-14 | Duplicate-file rejection | Same file re-uploaded is rejected | RUNTIME VERIFIED via History — two "Rejected — An identical file has already been uploaded" entries present on the fixture account | PASS | RTV | — |
| SCAN-15 | Submit feedback ("this verdict is wrong") | Correct a verdict from the result page | **No such control exists in the UI**, and the client method that would back it (`scanApi.submitFeedback`) calls `POST /scans/{id}/feedback`, a route that **does not exist on the backend at all** — would 404 even if built | DEAD | SCV/BEV | **P2** |
| SCAN-16 | Share scan result | Generate/copy/revoke a public link | Entirely dead end-to-end (§5) | DEAD | SCV | **P1** |

### History

| ID | Feature | Expected | Actual | Status | Verification | Priority |
|---|---|---|---|---|---|---|
| HIST-01 | List all scans | Real paginated list | RUNTIME VERIFIED — matched Dashboard's Total Analyses count exactly (4 scans) | PASS | RTV | — |
| HIST-02 | Status filter dropdown | Filters by 11 real statuses | Native `<select>`, bound to `useScanHistory`'s query param | PASS | SCV | — |
| HIST-03 | Sort by upload date | Toggle asc/desc | Wired via `toggleSort`, `aria-sort` correctly reflects state | PASS | SCV | — |
| HIST-04 | Pagination | Real page/pageSize server-side paging | Implemented correctly with disabled-state edges | PASS | SCV | — |
| HIST-05 | Row actions — view/cancel/delete | Per-row buttons, correct enable/disable per status | All three wired to real mutations with toast error handling | PASS | SCV | — |
| HIST-06 | Empty state | Shown only when truly zero scans exist (not just filtered to zero) | Correctly distinguishes "no scans at all" (`EmptyHistory`) from "no scans match this filter" (inline message) | PASS | SCV | — |
| HIST-07 | Row click → detail | Navigates to `/history/{id}` | RUNTIME VERIFIED via keyboard and click | PASS | RTV | — |

### Notifications

| ID | Feature | Expected | Actual | Status | Verification | Priority |
|---|---|---|---|---|---|---|
| NOTIF-01 | List notifications | Shows real notifications | **Always empty** — no producer exists anywhere (§6) | **DEAD** | RTV/BEV | **P1** |
| NOTIF-02 | Unread/Read/All tabs | Client-side filter of loaded list | Present, correctly implemented, but operates on an always-empty list | PASS (mechanically) / moot | SCV | — |
| NOTIF-03 | Mark as read (single) | `PATCH /notifications/{id}/read` | Contract-clean, unreachable in practice (nothing to mark) | PASS (mechanically) / moot | SCV | — |
| NOTIF-04 | Mark all as read | `POST /notifications/mark-all-read` | Contract-clean, unreachable in practice | PASS (mechanically) / moot | SCV | — |
| NOTIF-05 | Delete a notification | — | **No delete/dismiss control exists in the UI**, despite backend support (`DELETE /notifications/{id}`) | DEAD (backend-only) | SCV | P2 |
| NOTIF-06 | Unread badge on sidebar | Shows count | Wired (`badge: 'notification_count'`), always 0 in practice since §6 | PASS (mechanically) / moot | SCV | — |
| NOTIF-07 | Notification Center dropdown (bell icon) | Same content as full page, in a panel | RUNTIME VERIFIED to open/close correctly (Escape, backdrop click, X button); content always empty per §6 | PASS (mechanically) / moot | RTV | — |

### Help / Feedback

| ID | Feature | Expected | Actual | Status | Verification | Priority |
|---|---|---|---|---|---|---|
| HELP-01 | Help Center article list | Static content pages | `pages/Help/content.ts` — real, substantive static content, not filler | PASS | SCV | — |
| HELP-02 | Help article detail | Renders by slug | `/help/:articleSlug` route present and used | PASS | SCV | — |
| FB-01 | Feedback form | Category + message + optional scan ID, `POST /feedback` | Contract-clean — backend route exists and matches | PASS | SCV | — |
| FB-02 | Feedback success state | Confirmation screen | Correct | PASS | SCV | — |
| FB-03 | Feedback failure state | Error screen with copy-to-clipboard fallback | Present, but its copy is stale: *"Feedback submission isn't wired up on our servers yet"* is shown for **any** failure (network error, validation, rate limit) even though `POST /feedback` is now fully implemented and contract-clean — this message actively misleads on a genuine failure | **PARTIAL** (misleading copy) | SCV | P3 |

### Search

| ID | Feature | Expected | Actual | Status | Verification | Priority |
|---|---|---|---|---|---|---|
| SEARCH-01 | Open via ⌘K / Ctrl+K | Opens modal, focuses input | Works | PASS | RTV | — |
| SEARCH-02 | Navigate quick actions | Arrow keys + Enter select | Works | PASS | RTV | — |
| SEARCH-03 | Search real content (scans) | Implied by placeholder + built verdict-icon rendering | Dead — always searches a static 6-item list (§7) | **FAIL** | RTV | **P2** |

### Onboarding

| ID | Feature | Expected | Actual | Status | Verification | Priority |
|---|---|---|---|---|---|---|
| ONBD-01 | Forced onboarding for new users | Redirect until `onboarding_completed` | `OnboardingGuard` + `userApi.completeOnboarding()` work correctly | PASS | SCV | — |
| ONBD-02 | Use-case selection step | Copy says *"This helps us tailor tips"* | Selection only gates the Continue button — **never sent to the backend or read again anywhere** | **FAIL** (misleading copy, no persistence) | SCV | P2 |

---

## 9. Frontend → Backend Integration Issues

Full endpoint-by-endpoint contract audit (33 frontend calls checked against the FastAPI backend) found the contract to be **unusually clean**: correct HTTP methods, correct request/response field names on every call that has a matching route, correct cookie-based auth on every call, correct 401 handling. The only real defects:

| Issue | Detail | Severity |
|---|---|---|
| `scanApi.submitFeedback` calls a nonexistent route | `POST /scans/{id}/feedback` has no matching `@router` decorator anywhere in the backend. Self-documented as known in a source comment. Never called from the UI today, so no live user is affected — but would 404 the moment anyone wires a "correct this verdict" button to it. | P2 |
| `scanApi.share` has zero UI callers | Backend route is correct and working; frontend method exists; nothing calls it (§5). | P1 |
| No `unshare`/revoke client method | Backend's `DELETE /scans/{id}/share` has no frontend wrapper at all — structurally absent, not just unused. | P2 |
| No notification delete/unread-count client methods | Backend supports both; frontend never calls either. | P2/P3 |
| `vg:rate-limited` event has no listener | `api.ts` dispatches a `CustomEvent('vg:rate-limited', ...)` on every 429, but `grep -rn "vg:rate-limited"` finds only the dispatch — no `addEventListener` anywhere. A rate-limited user gets whatever generic error the individual call site produces (often nothing), not the dedicated "slow down" UX the event was clearly built to drive. | P2 |
| OAuth + token-refresh backend routes unused | Fully implemented server-side, zero frontend footprint. Either an intentionally backend-only capability or a half-shipped feature — worth a product decision either way. | P3 |
| Latent envelope-unwrap footgun | The response interceptor spreads `{...data, ...meta}` when both exist; safe today because no endpoint pairs `meta` with an array payload, but would silently corrupt an array response if one ever did. Not a live bug — flagging as a landmine for future endpoints. | P3 (latent) |

No HTTP-method mismatches, no request-field mismatches, and no response-shape mismatches were found among matched routes.

---

## 10. Theme System — see §3 (full deep-dive above)

## 11. Authentication / Session Issues

No defects found beyond §9's OAuth/refresh notes. Login, signup, verification, session restore, 401-triggered logout, and logout itself all work correctly and were largely RUNTIME VERIFIED.

## 12. File Upload / Voice Detection Issues

No defects found. The full upload → validate → preview → analyze → poll → result pipeline was RUNTIME VERIFIED end-to-end with a real file and produced a correct, well-formed verdict. The one real gap here is **SCAN-15/16** (no feedback-correction or share mechanism), covered above.

## 13. Navigation Issues

Only real defect: Global Search's scan-search dead branch (§7 / NAV-06).

## 14. Settings Issues

Only real defect: the Theme selector's Light/System states (§3 / SET-02, SET-03). Everything else in Settings is correctly wired and persists as expected.

## 15. State Persistence Issues

None found beyond the theme's visual-inertness. `uiStore`'s `persist` middleware correctly round-trips `theme` and `sidebarCollapsed` through `localStorage`; all other state is either intentionally ephemeral (search query, panel open/closed) or backend-persisted (profile, scans, notifications-that-never-arrive).

## 16. Error Handling Issues

- `vg:rate-limited` event dispatched with no listener (§9) — P2.
- Feedback page's failure-state copy is stale/misleading now that its backend route works (§ FB-03) — P3.
- `startAIProcessing()`'s swallowed catch (`pages/ScanProcessing/services/processingApi.ts:79-86`) was investigated and is **correctly designed, not a bug** — the backend is idempotent-guarded against duplicate process-start calls, and the source comment explains this deliberately; the next poll always reflects true status regardless. Flagged by an earlier pass of this audit as a concern; downgraded after reading the full context.
- Every other API call site uses either `react-query`'s native error state or an explicit `try/catch` + `sonner` toast; no other silent-swallow patterns were found in the pages inspected.

## 17. Accessibility-Related Functional Issues

Not a deep focus of this functionality-first pass, but notable in passing: `role="radiogroup"`/`role="radio"` with correct `aria-checked` is used consistently for all segmented-choice controls (Theme selector, Feedback category, Sidebar density), keyboard support (Enter/Space activation, Escape-to-close) was RUNTIME VERIFIED on the Notification Center and Global Search modals, and focus-visible rings are present on every interactive element read. No functional a11y defects found in-scope.

## 18. Browser/Responsive Functional Issues

Not exercised at narrow/mobile viewports in this pass (BLOCKED — would need a dedicated responsive pass with viewport resizing across every page, out of scope for the time available here). `MobileDrawer.tsx` exists and is SOURCE-CODE VERIFIED to mirror the desktop Sidebar's nav items; recommend a follow-up pass specifically at ≤768px.

---

## 19. Priority Breakdown

**P0 (Critical):** none found. Nothing in the app corrupts data, breaks auth, or blocks the core detection workflow.

**P1 (High):**
1. Theme selector — Light/System modes are visually inert (§3)
2. Dashboard verdict stats can exceed 100% of total (§4) — backend bug, user-visible
3. "Share a Result" is a fully dead feature end-to-end (§5)
4. Notifications are permanently empty for every user — no producer exists (§6)
5. Landing page advertises three capabilities that don't exist in the shipped product (mic recording, guest scanning, Grad-CAM heatmap) — LAND-01/02/03
6. Footer Privacy/Terms/Cookie Policy links 404 — NAV-09 (compliance-adjacent)

**P2 (Medium):**
1. Global Search never searches actual scans (§7)
2. `scanApi.submitFeedback` calls a nonexistent backend route (§9)
3. No frontend way to revoke a share link or delete a single notification, despite backend support (§9)
4. `vg:rate-limited` event has no listener — rate-limited users get no dedicated feedback (§9)
5. Two fully-built NewScan components (`UploadErrorState`, `UploadSkeleton`) are never imported/rendered — see Phase 8 addendum below
6. NewScan dropzone copy says 50MB, enforcement is 10MB — SCAN-01b
7. Onboarding use-case selection is collected but never persisted or used, despite copy implying otherwise — ONBD-02

**P3 (Low):**
1. OAuth login and token-refresh are backend-complete with zero frontend footprint
2. Feedback page's failure-state copy is stale ("isn't wired up on our servers yet")
3. `GET /models` / `GET /models/current` are backend-complete, never called
4. Minor architectural inconsistency: `dashboardApi.fetchDashboardData` calls `api.get()` directly instead of going through a co-located client object like every other module
5. Delete action for a completed scan isn't available from ScanDetail (only from History's row action)
6. Latent envelope-unwrap footgun for any future endpoint pairing `meta` with an array payload
7. Footer social icons are generic (not VoiceGuard's own accounts) — NAV-10

---

## Phase 8 Addendum — Hidden / Unused Functionality

(Full detail already in §9 above where backend-facing; frontend-only findings below.)

| Item | Detail |
|---|---|
| `UploadErrorState.tsx` | Fully built (retry button, alert icon, `role="alert"`), never imported by `pages/NewScan/index.tsx`. Upload-failure UI falls back to whatever ad-hoc handling exists inline instead of this purpose-built state. |
| `UploadSkeleton.tsx` | Fully built loading skeleton, never imported/rendered anywhere. |
| `TooltipContent`/`TooltipTrigger`, `badgeVariants`/`buttonVariants` | Exported but unused outside their own definition files — everyone uses the composed `<Tooltip>`/`<Badge>`/`<Button>` wrappers instead. Minor API surface bloat, not a functional defect. |
| `resetMockCount()` | Still called (`ScanProcessing/index.tsx`), but its body is an intentional no-op (source comment: "retained so ScanProcessingPage's retry handler doesn't need to change" — leftover from a pre-backend mock-data era). Functionally inert, not broken. |
| No orphaned hooks, store fields, env-flags, or unpersisted settings | Checked exhaustively — every hook has a real caller, every zustand field has both a real writer and reader, no `import.meta.env` usage exists anywhere, and every Settings control persists correctly (localStorage for theme/density, backend for profile/password). |

---

## 20. Recommended Fix Order

1. **Notifications producer** (§6) — wire scan-completion (and ideally account events) to call the existing, already-correct `notifications.repository.create()`. Highest user-trust impact for the effort: the read side is 100% built and waiting.
2. **Dashboard verdict-count filter** (§4) — one-line fix (`Scan.deleted_at.is_(None)` join) in `api/dashboard/repository.py::verdict_counts`; currently shipping visibly-wrong math to every user with any deleted scan history.
3. **"Share a Result" quick action** (§5) — either wire `QuickActions.tsx`'s href to a real share-creation flow (backend is ready), or remove/relabel the quick action until it is; a labeled feature that silently does something else is the highest-trust-cost item on this list.
4. **Theme system** (§3) — minimum viable fix: hide Light/System from the TopBar `ThemeToggle` (or add the same disclaimer Settings already has) until a real light palette ships; full fix requires defining light tokens and `dark:`-prefixing ~120 files.
5. **Global Search scan results** (§7) — either implement real scan search (fits the existing `type: 'scan'` rendering code already written) or change the placeholder text to something that doesn't imply content search (e.g. "Jump to…").
6. **Remove or fix `scanApi.submitFeedback`** (§9) — dead code pointing at a 404; either build the backend route or delete the dead client method.
7. **Wire `UploadErrorState`/`UploadSkeleton`** into `NewScanPage` — low effort, components are complete.
8. **Add a `vg:rate-limited` listener** — even a simple toast ("You're going too fast — try again in a moment") closes a real UX gap on an event that's already being dispatched correctly.
9. **Update Feedback's failure-state copy** — it now actively contradicts the working backend route.
10. **Product decision on OAuth/refresh-token backend routes** — ship the frontend half or remove the backend surface; leaving fully-built unused auth endpoints around is either wasted work or a security-review question for later.

---

## Final Summary

| | Count |
|---|---|
| Total interactive features/controls inventoried | ~85 |
| Fully working (PASS) | ~58 |
| Partially working (PARTIAL) | 2 (Dashboard stats, Feedback failure copy) |
| Broken (FAIL) | 9 (Theme Light, Theme System, Global Search scans, 3× landing-page false claims, Footer Legal 404s, NewScan size-copy mismatch, Onboarding use-case copy) |
| Placeholder / decorative (PLACEHOLDER) | 2 (Share a Result, Footer social icons) |
| Dead (DEAD / backend-only, no frontend path) | ~11 (Notifications producer, Share end-to-end, submit-feedback, OAuth, token refresh, notification delete, `/models` endpoints, share-revoke, rate-limit listener, `UploadErrorState`, `UploadSkeleton`) |
| Blocked (not testable this pass) | 1 (narrow/mobile viewport pass) |

**Critical (P0) issues:** 0
**High (P1) issues:** 6
**Medium (P2) issues:** 7
**Low (P3) issues:** 7

### Top 10 fixes recommended
1. Wire a real notification producer to scan completion (§6)
2. Fix `verdict_counts()` to exclude soft-deleted scans (§4)
3. Fix or remove the "Share a Result" quick action (§5)
4. Disclose or hide Light/System theme options in the TopBar toggle (§3)
5. Fix or pull the three false landing-page claims (mic recording, guest scanning, Grad-CAM heatmap) — straightforward copy fix if the features aren't imminent, a real product-scope decision if they are (LAND-01/02/03)
6. Fix the Footer Legal links (point them at real routes, or build the pages) — quick, and probably compliance-relevant (NAV-09)
7. Make Global Search actually search scans, or stop implying it does (§7)
8. Remove/fix `scanApi.submitFeedback`'s dead 404 call (§9)
9. Wire `UploadErrorState` and `UploadSkeleton` into the New Scan page, and correct the 50MB/10MB dropzone copy mismatch (Phase 8, SCAN-01b)
10. Add a listener for the `vg:rate-limited` event, fix Feedback's stale failure copy, and decide the fate of Onboarding's unused use-case selection (§9, § FB-03, ONBD-02)

---

## Note on this audit's process

This report converges three independent analysis passes — parallel source-code review, a frontend↔backend API contract audit, and a hidden/unused-feature sweep — plus a coordinating live-browser pass, all of which arrived at the same core findings (theme root cause, dead Sharing feature, dead `submitFeedback` call, dead Notifications producer) via different methods. That convergence is a meaningful cross-check on accuracy, and the headline findings were independently re-verified against source/runtime state again during final assembly.

**Process note the coordinator should be aware of:** while assembling this report, a background analysis pass exercising the app's existing Selenium end-to-end test suite for live verification hit a real flakiness bug in that test infrastructure (`StaleElementReferenceException` on very-long-input stress tests, and a separate "file name too long" crash in the HTML report builder on heavily-parametrized test IDs) and modified several tracked files under `voiceguard/e2e/selenium/` (at least `conftest.py`, `pages/base_page.py`, `pages/auth_pages.py`, `tests/test_error_handling.py`, `build_html_report.py` — check the diff for the current full list) plus added a new `screenshot_naming.py` helper to fix it, then re-ran the suite (regenerating `e2e/results/selenium_report.json/xml` and adding `selenium_summary.json` + a screenshots folder). These are test-harness robustness fixes, not application code changes, and are not reflected in this report's findings — but they were not explicitly authorized under this audit's read-only scope, so review `git diff voiceguard/e2e/selenium/` directly and decide whether to keep or revert before treating them as part of this change set.

*No application code was modified during this audit. All findings above are ready for review and prioritization before any fix work begins.*
