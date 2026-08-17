import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster, toast } from 'sonner'
import { Capacitor } from '@capacitor/core'
import { App as CapacitorApp } from '@capacitor/app'
import { StatusBar, Style } from '@capacitor/status-bar'
import { SplashScreen } from '@capacitor/splash-screen'
import { LandingPage } from '@/pages/LandingPage'
import { AppShell } from '@/components/layout/AppShell'
import { AuthGuard } from '@/guards/AuthGuard'
import { GuestGuard } from '@/guards/GuestGuard'
import { OnboardingGuard } from '@/guards/OnboardingGuard'
import { useAuthStore } from '@/store/authStore'
import { useResolvedTheme } from '@/hooks/useResolvedTheme'
import { DashboardPage } from '@/pages/Dashboard'
import { NewScanPage } from '@/pages/NewScan'
import { ScanProcessingPage } from '@/pages/ScanProcessing'
import { ScanResultPage } from '@/pages/ScanResult'
import { HistoryPage } from '@/pages/History'
import { ScanDetailPage } from '@/pages/ScanDetail'
import { SignupPage } from '@/pages/Signup'
import { LoginPage } from '@/pages/Login'
import { VerifyEmailPage } from '@/pages/VerifyEmail'
import { ForgotPasswordPage } from '@/pages/ForgotPassword'
import { ResetPasswordPage } from '@/pages/ResetPassword'
import { NotificationsPage } from '@/pages/Notifications'
import { HelpCenterPage } from '@/pages/Help'
import { HelpArticlePage } from '@/pages/Help/Article'
import { FeedbackPage } from '@/pages/Feedback'
import { ProfilePage } from '@/pages/Settings/Profile'
import { AccountPage } from '@/pages/Settings/Account'
import { AppearancePage } from '@/pages/Settings/Appearance'
import { SharedResultPage } from '@/pages/SharedResult'
import { OnboardingPage } from '@/pages/Onboarding'

// ─── App init ─────────────────────────────────────────────────────────────────

function AppInit() {
  const checkSession = useAuthStore((s) => s.checkSession)
  useEffect(() => { checkSession() }, [checkSession])

  // Android hardware back button (Phase 14). Registering a listener replaces
  // the plugin's default handler (bare exitApp/webview-back), so this is
  // responsible for the whole policy: close an open Radix dialog first (they
  // don't push history entries, so browser back can't reach them), otherwise
  // fall back to the SPA's own navigation history, and only exit at a true
  // root with nothing left to go back to.
  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return
    const listenerPromise = CapacitorApp.addListener('backButton', ({ canGoBack }) => {
      const openDialog = document.querySelector(
        '[role="dialog"][data-state="open"], [role="alertdialog"][data-state="open"]'
      )
      if (openDialog) {
        openDialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }))
        return
      }
      if (canGoBack) {
        window.history.back()
      } else {
        CapacitorApp.exitApp()
      }
    })
    return () => { void listenerPromise.then((handle) => handle.remove()) }
  }, [])

  // Splash screen (Phase 15): capacitor.config.ts sets launchAutoHide: false
  // so the native splash stays up through the session-check network round
  // trip above, instead of flashing a blank/loading WebView first.
  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return
    void SplashScreen.hide()
  }, [])

  // api.ts dispatches this on every 429 (login/register/scan-create/etc. all
  // have per-route rate limits — see api/core/rate_limit.py); mounted here,
  // globally and unconditionally, since a 429 can happen on pre-auth routes
  // (login, register, forgot-password) just as easily as authenticated ones.
  useEffect(() => {
    const handler = (e: Event) => {
      const retryAfter = (e as CustomEvent<{ retryAfter?: string }>).detail?.retryAfter
      const seconds = retryAfter ? Number(retryAfter) : NaN
      toast.error(
        Number.isFinite(seconds) && seconds > 0
          ? `You're going too fast — try again in ${seconds}s.`
          : "You're going too fast — try again in a moment."
      )
    }
    window.addEventListener('vg:rate-limited', handler)
    return () => window.removeEventListener('vg:rate-limited', handler)
  }, [])

  return null
}

// ─── Root ─────────────────────────────────────────────────────────────────────

// Phase 15: keep the status bar icons legible against the app's own
// header/background instead of the OS default, and let the WebView lay out
// below the status bar (setOverlaysWebView(false)) rather than auditing
// every screen for safe-area-inset padding by hand.
function NativeStatusBar() {
  const resolvedTheme = useResolvedTheme()

  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return
    void StatusBar.setOverlaysWebView({ overlay: false })
    void StatusBar.setStyle({ style: resolvedTheme === 'dark' ? Style.Dark : Style.Light })
  }, [resolvedTheme])

  return null
}

function ThemedToaster() {
  const resolvedTheme = useResolvedTheme()
  return (
    <Toaster
      position="bottom-right"
      theme={resolvedTheme}
      toastOptions={{
        classNames: {
          toast: 'bg-bg-elevated border border-chrome/8 text-text-primary rounded-xl',
        },
      }}
    />
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInit />
      <NativeStatusBar />

      <Routes>
        {/* ── Public routes ─────────────────────────────────── */}
        <Route path="/" element={<LandingPage />} />

        <Route
          path="/signup"
          element={
            <GuestGuard>
              <SignupPage />
            </GuestGuard>
          }
        />
        <Route
          path="/login"
          element={
            <GuestGuard>
              <LoginPage />
            </GuestGuard>
          }
        />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route
          path="/forgot-password"
          element={
            <GuestGuard>
              <ForgotPasswordPage />
            </GuestGuard>
          }
        />
        <Route
          path="/reset-password"
          element={
            <GuestGuard>
              <ResetPasswordPage />
            </GuestGuard>
          }
        />

        {/* Shared result — public, no shell */}
        <Route path="/r/:scanId" element={<SharedResultPage />} />

        {/* ── Onboarding — auth required, no main shell ────── */}
        <Route
          path="/onboarding"
          element={
            <AuthGuard>
              <OnboardingPage />
            </AuthGuard>
          }
        />

        {/* ── Authenticated app shell ───────────────────────── */}
        <Route
          element={
            <AuthGuard>
              <OnboardingGuard>
                <AppShell />
              </OnboardingGuard>
            </AuthGuard>
          }
        >
          <Route path="/dashboard" element={<DashboardPage />} />

          {/* Detection */}
          <Route path="/scan/new" element={<NewScanPage />} />
          <Route path="/scan/processing" element={<ScanProcessingPage />} />
          <Route path="/scan/:scanId" element={<ScanResultPage />} />

          {/* History */}
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/history/:scanId" element={<ScanDetailPage />} />

          {/* Notifications */}
          <Route path="/notifications" element={<NotificationsPage />} />

          {/* Help */}
          <Route path="/help" element={<HelpCenterPage />} />
          <Route path="/help/:articleSlug" element={<HelpArticlePage />} />

          {/* Feedback */}
          <Route path="/feedback" element={<FeedbackPage />} />

          {/* Settings */}
          <Route path="/settings" element={<Navigate to="/settings/profile" replace />} />
          <Route path="/settings/profile" element={<ProfilePage />} />
          <Route path="/settings/account" element={<AccountPage />} />
          <Route path="/settings/appearance" element={<AppearancePage />} />
        </Route>

        {/* ── 404 ──────────────────────────────────────────── */}
        <Route
          path="*"
          element={
            <div className="min-h-screen bg-bg-base flex items-center justify-center">
              <div className="text-center">
                <h1 className="text-display-md font-bold text-text-primary mb-4">404</h1>
                <p className="text-text-secondary mb-8">This page doesn't exist.</p>
                <a href="/" className="btn-primary">Return home</a>
              </div>
            </div>
          }
        />
      </Routes>

      {/* Global toast notifications */}
      <ThemedToaster />
    </BrowserRouter>
  )
}
