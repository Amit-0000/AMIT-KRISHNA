import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { LandingPage } from '@/pages/LandingPage'
import { AppShell } from '@/components/layout/AppShell'
import { AuthGuard } from '@/guards/AuthGuard'
import { GuestGuard } from '@/guards/GuestGuard'
import { OnboardingGuard } from '@/guards/OnboardingGuard'
import { useAuthStore } from '@/store/authStore'
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
  return null
}

// ─── Root ─────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <BrowserRouter>
      <AppInit />

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
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#141428',
            border: '1px solid rgba(255,255,255,0.08)',
            color: '#F0F0FF',
            borderRadius: '12px',
          },
        }}
      />
    </BrowserRouter>
  )
}
