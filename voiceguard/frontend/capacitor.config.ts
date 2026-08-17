import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.voiceguard.app',
  appName: 'VoiceGuard',
  webDir: 'dist',
  android: {
    // 'https' (not the default capacitor:// scheme) so the WebView's origin
    // is https://localhost — matters for cookie acceptance behavior on some
    // Android WebView versions and is the origin api/auth/router.py's
    // _is_mobile_client checks for. See ANDROID_APP.md.
    //
    // allowMixedContent must be true: confirmed via a real device run that
    // Chromium's Mixed Content policy (separate from, and in addition to,
    // Android's own cleartext-traffic restriction) blocks an HTTPS-origin
    // page from making plain-HTTP XHR/fetch calls at all — this bit even
    // with the debug-only cleartext manifest exemption already in place, as
    // "Mixed Content: ... This request has been blocked" in logcat, not a
    // network error. Only matters for local/CI testing against a plain-HTTP
    // backend (VITE_API_BASE_URL=http://10.0.2.2:8000, see ANDROID_APP.md);
    // the real production backend is HTTPS, so this is a no-op there.
    allowMixedContent: true,
  },
  server: {
    androidScheme: 'https',
  },
  plugins: {
    SplashScreen: {
      // App.tsx's AppInit calls SplashScreen.hide() once session bootstrap
      // has run, instead of the default timed auto-hide racing that network
      // call and briefly showing a blank WebView.
      launchAutoHide: false,
      backgroundColor: '#08080f', // matches index.css's --color-bg-base dark value
      androidScaleType: 'CENTER_CROP',
      showSpinner: false,
    },
  },
}

export default config
