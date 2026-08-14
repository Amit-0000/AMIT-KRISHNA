import { useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Shield } from 'lucide-react'
import { useUIStore } from '@/store/uiStore'
import { SIDEBAR_SECTIONS, SETTINGS_NAV } from './nav-config'
import { UserMenu } from './UserMenu'
import { cn } from '@/lib/utils'

export function MobileDrawer() {
  const isOpen = useUIStore((s) => s.mobileDrawerOpen)
  const setOpen = useUIStore((s) => s.setMobileDrawerOpen)
  const unreadCount = useUIStore((s) => s.unreadCount)
  const location = useLocation()

  // Close on route change
  useEffect(() => {
    setOpen(false)
  }, [location.pathname, setOpen])

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, setOpen])

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [isOpen])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            key="drawer-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />

          {/* Drawer */}
          <motion.aside
            key="drawer-panel"
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ duration: 0.28, ease: [0.25, 0, 0, 1] }}
            className="fixed left-0 top-0 h-full w-72 z-50 bg-bg-surface border-r border-chrome/6 flex flex-col lg:hidden"
            role="dialog"
            aria-label="Navigation menu"
            aria-modal="true"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 h-14 border-b border-chrome/6 flex-shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-brand-muted border border-brand-border">
                  <Shield className="w-4 h-4 text-brand" aria-hidden="true" />
                  <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-human" aria-hidden="true" />
                </div>
                <span className="font-semibold text-base text-text-primary tracking-tight">
                  Voice<span className="text-brand">Guard</span>
                </span>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="flex items-center justify-center w-8 h-8 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-chrome/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                aria-label="Close navigation"
              >
                <X className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>

            {/* Nav */}
            <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6" aria-label="Mobile navigation">
              {SIDEBAR_SECTIONS.map((section) => (
                <div key={section.id}>
                  {section.label && (
                    <p className="px-2 mb-2 text-[10px] font-semibold text-text-tertiary uppercase tracking-widest">
                      {section.label}
                    </p>
                  )}
                  <ul className="space-y-0.5" role="list">
                    {section.items.map((item) => {
                      const Icon = item.icon
                      const badge = item.badge === 'notification_count' ? unreadCount : 0
                      const isActive = item.matchExact
                        ? location.pathname === item.href
                        : location.pathname.startsWith(item.href)

                      return (
                        <li key={item.id}>
                          <NavLink
                            to={item.href}
                            end={item.matchExact}
                            className={cn(
                              'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors duration-150',
                              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                              isActive
                                ? item.id === 'new-scan'
                                  ? 'bg-brand text-white'
                                  : 'bg-brand-muted text-brand'
                                : item.id === 'new-scan'
                                ? 'bg-brand/10 text-brand hover:bg-brand hover:text-white'
                                : 'text-text-secondary hover:bg-chrome/5 hover:text-text-primary'
                            )}
                            aria-current={isActive ? 'page' : undefined}
                          >
                            <Icon className="w-4.5 h-4.5 flex-shrink-0" aria-hidden="true" />
                            <span className="flex-1">{item.label}</span>
                            {badge > 0 && (
                              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-brand text-white text-[10px] font-bold">
                                {badge > 9 ? '9+' : badge}
                              </span>
                            )}
                          </NavLink>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              ))}

              {/* Settings */}
              <div>
                <ul className="space-y-0.5" role="list">
                  {(() => {
                    const Icon = SETTINGS_NAV.icon
                    const isActive = location.pathname.startsWith('/settings')
                    return (
                      <li>
                        <NavLink
                          to={SETTINGS_NAV.href}
                          className={cn(
                            'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors duration-150',
                            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                            isActive
                              ? 'bg-brand-muted text-brand'
                              : 'text-text-secondary hover:bg-chrome/5 hover:text-text-primary'
                          )}
                          aria-current={isActive ? 'page' : undefined}
                        >
                          <Icon className="w-4.5 h-4.5 flex-shrink-0" aria-hidden="true" />
                          Settings
                        </NavLink>
                      </li>
                    )
                  })()}
                </ul>
              </div>
            </nav>

            {/* User */}
            <div className="border-t border-chrome/6 px-3 py-3 flex-shrink-0">
              <UserMenu collapsed={false} />
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
