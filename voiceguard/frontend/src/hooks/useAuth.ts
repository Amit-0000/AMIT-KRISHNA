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
  const checkSession = useAuthStore((s) => s.checkSession)

  useEffect(() => {
    checkSession()
  }, [checkSession])

  // Listen for 401 events from the API interceptor
  useEffect(() => {
    const handler = () => setUser(null)
    window.addEventListener('vg:unauthorized', handler)
    return () => window.removeEventListener('vg:unauthorized', handler)
  }, [setUser])

  return { user, isAuthenticated, isLoading, logout, setUser }
}
