import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AppNotification, Theme } from '@/types'

const STORAGE_KEY = 'vg-ui'

interface UIState {
  // Sidebar
  sidebarCollapsed: boolean
  mobileDrawerOpen: boolean
  toggleSidebar: () => void
  setSidebarCollapsed: (v: boolean) => void
  setMobileDrawerOpen: (v: boolean) => void

  // Search
  searchOpen: boolean
  setSearchOpen: (v: boolean) => void

  // Notifications
  notificationPanelOpen: boolean
  notifications: AppNotification[]
  unreadCount: number
  setNotificationPanelOpen: (v: boolean) => void
  setNotifications: (items: AppNotification[]) => void
  markNotificationRead: (id: string) => void
  markAllNotificationsRead: () => void
  removeNotification: (id: string) => void

  // Theme
  theme: Theme
  setTheme: (t: Theme) => void
}

function applyTheme(theme: Theme) {
  const root = document.documentElement
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const isDark = theme === 'dark' || (theme === 'system' && prefersDark)
  root.classList.toggle('dark', isDark)
  root.classList.toggle('light', !isDark)
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      // ── Sidebar ────────────────────────────────────────────────────────────
      sidebarCollapsed: false,
      mobileDrawerOpen: false,

      toggleSidebar: () =>
        set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),

      setMobileDrawerOpen: (v) => set({ mobileDrawerOpen: v }),

      // ── Search ─────────────────────────────────────────────────────────────
      searchOpen: false,
      setSearchOpen: (v) => set({ searchOpen: v }),

      // ── Notifications ──────────────────────────────────────────────────────
      notificationPanelOpen: false,
      notifications: [],
      unreadCount: 0,

      setNotificationPanelOpen: (v) => {
        set({ notificationPanelOpen: v })
        // Close search when opening notifications and vice-versa
        if (v) set({ searchOpen: false })
      },

      setNotifications: (items) =>
        set({ notifications: items, unreadCount: items.filter((n) => !n.read).length }),

      markNotificationRead: (id) =>
        set((s) => {
          const notifications = s.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          )
          return { notifications, unreadCount: notifications.filter((n) => !n.read).length }
        }),

      markAllNotificationsRead: () =>
        set((s) => ({
          notifications: s.notifications.map((n) => ({ ...n, read: true })),
          unreadCount: 0,
        })),

      removeNotification: (id) =>
        set((s) => {
          const notifications = s.notifications.filter((n) => n.id !== id)
          return { notifications, unreadCount: notifications.filter((n) => !n.read).length }
        }),

      // ── Theme ──────────────────────────────────────────────────────────────
      theme: 'dark',

      setTheme: (theme) => {
        set({ theme })
        applyTheme(theme)
      },
    }),
    {
      name: STORAGE_KEY,
      partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed, theme: s.theme }),
      onRehydrateStorage: () => (state) => {
        if (state) applyTheme(state.theme)
      },
    }
  )
)

// Listen for system theme changes
if (typeof window !== 'undefined') {
  window
    .matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', () => {
      const { theme } = useUIStore.getState()
      if (theme === 'system') applyTheme('system')
    })
}
