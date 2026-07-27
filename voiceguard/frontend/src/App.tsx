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

// ─── Placeholder page ─────────────────────────────────────────────────────────
// Each screen gets replaced when it is implemented. These stubs let the shell
// compile and render correctly while subsequent screens are being built.

function ComingSoon({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center">
        <p className="text-xs font-semibold text-brand uppercase tracking-widest mb-3">
          Coming next
        </p>
        <h1 className="text-display-sm font-bold text-text-primary mb-2">{label}</h1>
        <p className="text-sm text-text-secondary">
          This screen is being implemented.
        </p>
      </div>
    </div>
  )
}

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
              <ComingSoon label="S02 — Sign Up" />
            </GuestGuard>
          }
        />
        <Route
          path="/login"
          element={
            <GuestGuard>
              <ComingSoon label="S03 — Login" />
            </GuestGuard>
          }
        />
        <Route path="/verify-email" element={<ComingSoon label="S04 — Email Verification" />} />
        <Route path="/forgot-password" element={<ComingSoon label="S05 — Forgot Password" />} />

        {/* Shared result — public, no shell */}
        <Route path="/r/:scanId" element={<ComingSoon label="S20 — Shared Result" />} />

        {/* ── Onboarding — auth required, no main shell ────── */}
        <Route
          path="/onboarding"
          element={
            <AuthGuard>
              <ComingSoon label="S06 — Onboarding" />
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
          <Route path="/scan/:scanId" element={<ComingSoon label="S10 — Scan Result" />} />

          {/* History */}
          <Route path="/history" element={<ComingSoon label="S11 — History" />} />
          <Route path="/history/:scanId" element={<ComingSoon label="S12 — Scan Detail" />} />

          {/* Notifications */}
          <Route path="/notifications" element={<ComingSoon label="S13 — Notifications" />} />

          {/* Help */}
          <Route path="/help" element={<ComingSoon label="S14 — Help Center" />} />
          <Route path="/help/:articleSlug" element={<ComingSoon label="S15 — Help Article" />} />

          {/* Feedback */}
          <Route path="/feedback" element={<ComingSoon label="S16 — Feedback" />} />

          {/* Settings */}
          <Route path="/settings" element={<Navigate to="/settings/profile" replace />} />
          <Route path="/settings/profile" element={<ComingSoon label="S17 — Profile" />} />
          <Route path="/settings/account" element={<ComingSoon label="S18 — Account Settings" />} />
          <Route path="/settings/appearance" element={<ComingSoon label="S19 — Appearance" />} />
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
