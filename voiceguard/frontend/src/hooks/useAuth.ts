import { useEffect } from 'react'
import { useAuthStore } from '@/store/authStore'
import type { User } from '@/types'

export interface AuthHook {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  logout: () => Promise<void>
  setUser: (user: User | null) => void
}

export function useAuth(): AuthHook {
  const user = useAuthStore((s) => s.user)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const isLoading = useAuthStore((s) => s.isLoading)
  const logout = useAuthStore((s) => s.logout)
  const setUser = useAuthStore((s) => s.setUser)

  // Session bootstrap runs once for the app's lifetime in <AppInit> (App.tsx).
  // Do not also call checkSession() here: this hook is used by components
  // (e.g. UserMenu) that live inside <AuthGuard>'s children, which unmounts
  // its children while isLoading is true. Triggering another checkSession()
  // on mount would flip isLoading, unmount this component, flip it back,
  // remount it, and re-trigger the check -- an infinite loop.

  // Listen for 401 events from the API interceptor
  useEffect(() => {
    const handler = () => setUser(null)
    window.addEventListener('vg:unauthorized', handler)
    return () => window.removeEventListener('vg:unauthorized', handler)
  }, [setUser])

  return { user, isAuthenticated, isLoading, logout, setUser }
}
