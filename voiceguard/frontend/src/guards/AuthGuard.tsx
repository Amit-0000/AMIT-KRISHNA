import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { Shield } from 'lucide-react'

interface AuthGuardProps {
  children: ReactNode
}

function SessionLoader() {
  return (
    <div
      className="fixed inset-0 bg-bg-base flex items-center justify-center"
      aria-label="Checking authentication…"
      role="status"
    >
      <div className="flex flex-col items-center gap-4">
        <div className="relative flex items-center justify-center w-12 h-12 rounded-2xl bg-brand-muted border border-brand-border animate-pulse-brand">
          <Shield className="w-6 h-6 text-brand" aria-hidden="true" />
        </div>
        <p className="text-sm text-text-secondary">Authenticating…</p>
      </div>
    </div>
  )
}

export function AuthGuard({ children }: AuthGuardProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const isLoading = useAuthStore((s) => s.isLoading)
  const location = useLocation()

  if (isLoading) return <SessionLoader />

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        state={{ from: location.pathname }}
        replace
      />
    )
  }

  return <>{children}</>
}
