# VoiceGuard Android App

A real Android application wrapping the existing VoiceGuard React/Vite frontend via
[Capacitor](https://capacitorjs.com/), talking to the same production Railway backend the web
app already uses. No React Native, no Flutter, no separate mobile backend, no on-device ML —
inference stays server-side exactly as it is today.

```
React/Vite frontend
      │
      ├── Vercel (web, unchanged)
      │
      └── Capacitor → Android APK
                          │
                        HTTPS
                          │
                     Railway FastAPI → PostgreSQL / Redis / LCNN·AudioCNN
```

## Architecture notes — read this before touching auth or API config

**Authentication is dual-mode.** The web app authenticates with httponly, `SameSite=Strict`
cookies (`api/auth/service.py`), which only works because Vercel's `rewrites`
(`frontend/vercel.json`) make the browser see the frontend and API as the same origin. The
Android app's WebView runs on its own origin (`https://localhost` — `capacitor.config.ts`'s
`androidScheme: 'https'`) and calls the Railway API cross-origin directly, so those cookies are
accepted at login but **never sent back** on later requests.

The backend additively returns raw access/refresh tokens in the JSON body when the request's
`Origin` is `https://localhost` or `capacitor://localhost` (`api/auth/router.py`'s
`_is_mobile_client` / `_MOBILE_APP_ORIGINS`). The Android app stores them via
`@capacitor/preferences` and sends them back as `Authorization: Bearer <token>`
(`frontend/src/services/api.ts`'s `isNativeApp` branch). The web app never triggers this path —
nothing about its cookie flow changed.

**Required production config change:** `ALLOWED_ORIGINS` on the real deployment (Railway) must
include `https://localhost`, or CORS blocks the Android app's requests before any of the above
matters. This is a manual step — nothing in this repo changes your live Railway environment
variables for you. `api/.env.example` already includes it for local/dev use.

**Malware scanning behavior is unchanged.** `MALWARE_SCAN_REQUIRED=false` in production still
means an unscanned upload proceeds with `malware_status: NOT_SCANNED`, never reported as "safe" —
same as the web app, nothing Android-specific here.

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Node.js | 22+ | matches `frontend/package.json` / CI |
| Java (JDK) | 21 | Temurin recommended — required by `@independo/capacitor-voice-recorder` and AGP 8.13 |
| Android SDK | API 33+ (compile/target 36) | via Android Studio, or `sdkmanager` standalone |
| Android Studio | latest (optional) | only needed for `npx cap open android` / a GUI, not for CLI builds |

GitHub-hosted `ubuntu-latest` runners already ship a compatible Android SDK — CI only needs
`actions/setup-java` on top (see `.github/workflows/android-app.yml`).

## Local development

```bash
cd frontend
npm install
npm run build          # tsc -b && vite build
npx cap sync android    # copies dist/ into the native project, updates plugins
npx cap open android    # opens Android Studio, or:
cd android && ./gradlew assembleDebug   # (Linux/macOS)
android\gradlew.bat assembleDebug        # (Windows)
```

The debug APK lands at `android/app/build/outputs/apk/debug/app-debug.apk`. Install it:

```bash
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

### Pointing a local build at a different backend

By default (no env override) the app talks to the production Railway backend — this is correct
for anything you intend to actually install and use. To point a local debug build at a different
backend (e.g. a docker-compose stack, reachable from an emulator at `10.0.2.2`, or a LAN IP for a
physical device):

```bash
VITE_API_BASE_URL=http://10.0.2.2:8000 npm run build
```

**Never build this way for anything other than local/CI testing.** A `localhost`/`10.0.2.2`-pointing
build handed to a real user or device outside that context is broken by construction — the device
can't reach your machine's loopback address. See `frontend/.env.example`.

If you point the app at plain HTTP (no TLS) for local testing, Android will block the request
(cleartext traffic is disallowed by default) — except this is already exempted for debug builds
only via the committed `android/app/src/debug/AndroidManifest.xml` override (Gradle merges
`src/debug/` into the debug build type only; the release manifest has no such exemption, and the
real production backend is HTTPS regardless).

## Microphone recording

Real device recording, not a browser `getUserMedia` shim — Android's WebView doesn't forward
`getUserMedia`'s permission prompt to the OS by default, so this uses
[`@independo/capacitor-voice-recorder`](https://www.npmjs.com/package/@independo/capacitor-voice-recorder),
a native plugin wrapping Android's `MediaRecorder`. On Android this plugin hardcodes raw AAC/ADTS
output (`audio/aac`, `.aac` — not an `.m4a`/MP4 container; confirmed via a real device recording
during testing, not assumed), which is an accepted format
(`api/core/audio_formats.ALLOWED_AUDIO_EXTENSIONS`) decoded through the same soundfile/ffmpeg
fallback `.mp3`/`.m4a` already use. Recordings feed into the **exact same** validate → upload →
poll → result pipeline as a browsed/dropped file
(`frontend/src/pages/NewScan/hooks/useFileUpload.ts`'s `handleRecordedFile`) — not a parallel
mobile-only path.

UI: `frontend/src/pages/NewScan/index.tsx` shows an Upload/Record toggle only when
`Capacitor.isNativePlatform()` is true; `components/RecordAudioPanel.tsx` +
`hooks/useAudioRecorder.ts` implement start/stop/play/re-record/analyze and the three permission
states (granted, denied — retry, permanently denied — routes to Android Settings via
`capacitor-native-settings`).

Required manifest permission (already added, `android/app/src/main/AndroidManifest.xml`):
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

## File upload

Uses the existing plain `<input type="file" accept="audio/*,...">` (`UploadDropzone.tsx`)
unchanged — Android's WebView already opens the native document/file picker for a standard file
input with zero extra plugin code. No new permission is required (scoped-storage document
picking on API 24+ doesn't need `READ_EXTERNAL_STORAGE`).

## Theme, back button, status bar, splash screen

- **Theme** (`frontend/src/pages/Settings/Appearance`) — Light/Dark/System already worked via CSS
  variables + `useResolvedTheme`; unchanged for Android. `App.tsx`'s `NativeStatusBar` additionally
  syncs the Android status bar icon color to the resolved theme.
- **Hardware back button** — `App.tsx`'s `AppInit` registers `@capacitor/app`'s `backButton`
  listener: closes an open Radix dialog first (dispatches a synthetic `Escape` keydown — dialogs
  don't push history entries, so plain back navigation can't reach them), otherwise
  `window.history.back()`, and only calls `exitApp()` when there's truly no history left.
- **Splash screen** — `capacitor.config.ts` sets `launchAutoHide: false` so the native splash
  stays up through the session-check network round trip instead of flashing a blank WebView;
  `AppInit` calls `SplashScreen.hide()` once that check resolves.
- **Status bar overlap** — `StatusBar.setOverlaysWebView({ overlay: false })` pushes WebView
  content below the status bar, instead of auditing every screen for safe-area-inset padding by
  hand.
- **App icon/splash image** — currently Capacitor's default generated assets (no VoiceGuard brand
  icon file exists in the repo to generate from). Once one exists, regenerate via
  `npx @capacitor/assets generate --android`.

## Testing

### Manual (real device / emulator) — do this before trusting a release

1. Install the debug APK (`adb install -r ...`).
2. Registration → email verification (check the real inbox/Resend/console log per
   `api/.env.example`'s `EMAIL_PROVIDER`) → login.
3. New Scan → Upload Audio → pick a real audio file → confirm real AI result.
4. New Scan → Record Audio → grant mic permission → record → stop → play back → analyze → confirm
   real AI result.
5. History, scan detail, share, notifications, theme switching (Light/Dark/System), logout,
   login again, forgot password → reset password.
6. Deny mic permission once (see "Try Again" state), deny twice (see "Open Settings" state),
   confirm tapping it opens the app's Android settings page.
7. Press the hardware back button from a detail page, from an open modal (e.g. notifications
   panel), and from the dashboard (should exit, not silently no-op).

No mocked responses — every one of the above hits the real Railway backend and real ML pipeline.

### Automated — Appium against the packaged APK

`voiceguard/e2e/appium-android/` is a new suite, sibling to the existing mobile-web suite
(`voiceguard/e2e/appium/`, which drives mobile Chrome — there was no native client before this).
It reuses that suite's page objects directly (pure CSS/XPath Selenium wrappers with no
browser-specific assumptions) rather than forking a second copy.

Covers: app launch, login, native-only Upload/Record toggle rendering, the real Android
microphone permission dialog, real recording, analyzing a recording through the real
upload → AI inference → result pipeline, history, theme toggle, the hardware back button, and
logout.

**Known, disclosed gap:** driving Android's system file/document picker (a separate app,
`DocumentsUI`) to test the upload path end-to-end is not automated — that picker's UI differs
across Android versions/OEMs and would need its own verified locator set. The record → analyze →
result flow above exercises the identical upload/scan/inference/result pipeline a picked file
would use, so that pipeline is still covered — just via the microphone path, not the file picker.

Run locally (needs Appium server + emulator + a built debug APK — see
`e2e/appium-android/conftest.py`):

```bash
cd e2e
pip install -r requirements.txt
appium &
cd appium-android
VOICEGUARD_APK_PATH=/path/to/app-debug.apk pytest -v
```

Gated by a real, configurable pass-rate threshold, same pattern as the existing Selenium/mobile-web
suites (`APPIUM_ANDROID_MIN_PASS_RATE`, default 90 — see `check_pass_threshold.py`).

## GitHub Actions

`.github/workflows/android-app.yml`:

1. **build-apk-for-artifact** — builds the frontend against the real production Railway API (no
   `VITE_API_BASE_URL` override), `cap sync`, Gradle `assembleDebug`, uploads the APK as a
   GitHub Actions artifact. This is the one build meant for a person to actually install.
2. **appium-android-tests** — builds a *separate* debug APK pointed at an isolated docker-compose
   backend (`VITE_API_BASE_URL=http://10.0.2.2:8000`, the Android-emulator alias for the runner's
   own localhost), boots a cached-AVD emulator (same KVM-permissions/snapshot-caching approach as
   `qa-suite.yml`'s `appium-tests` job), installs the APK, and runs the suite above with a real
   pass-rate gate. This build never leaves CI.
3. **summary** — fails the workflow if either blocking job didn't succeed.

No production secrets are required to build or test — the artifact build talks to the already-public
production API URL, and the test build talks to a locally-provisioned throwaway backend.

## Release signing

**Not configured, and this repo will not generate or embed a signing key for you.** The workflow
only ever produces a debug APK. To produce a signed release build:

1. Generate a keystore yourself (never commit it):
   ```bash
   keytool -genkey -v -keystore voiceguard-release.keystore -alias voiceguard -keyalg RSA -keysize 2048 -validity 10000
   ```
2. Store the keystore file, its password, the key alias, and the key password as GitHub Secrets
   (e.g. `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`,
   `ANDROID_KEY_PASSWORD`).
3. Add a `signingConfigs.release` block to `android/app/build.gradle` reading those from
   environment variables, and wire it into `buildTypes.release`.

This is a deliberate stop point (see the task's own STOP conditions) — signing credentials are
yours to create and hold, not something to be generated on your behalf.

## Troubleshooting

- **"No chromedriver found" in `appium-android-tests`** — the API 33 `google_apis` emulator
  image's Android System WebView build may not match the chromedriver version pinned for the
  sibling mobile-web suite (that pin is for the standalone Chrome *browser* app, a different
  component that can be on a different version). Appium's own error names the version it
  actually needed; fetch that chromedriver and set it via the `CHROMEDRIVER_EXECUTABLE` env var
  in the workflow, same mechanism the mobile-web suite already uses.
- **Login works but every subsequent request 401s** — almost always `ALLOWED_ORIGINS` on the
  target backend missing `https://localhost` (see "Required production config change" above).
- **Cleartext/`ERR_CLEARTEXT_NOT_PERMITTED`** — only possible on a *release* build (debug builds
  already exempt cleartext via the committed `src/debug/AndroidManifest.xml`); never add that
  exemption to a release build.
- **Emulator boot / KVM slowness in CI** — already solved once for this repo; see
  `qa-suite.yml`'s `appium-tests` job comments (KVM udev rule, AVD snapshot caching) — this
  workflow reuses the identical approach.
