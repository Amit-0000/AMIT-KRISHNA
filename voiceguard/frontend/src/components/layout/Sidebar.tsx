import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Shield, PanelLeftClose, PanelLeft } from 'lucide-react'
import { useUIStore } from '@/store/uiStore'
import { Tooltip, TooltipProvider } from '@/components/ui/tooltip'
import { UserMenu } from './UserMenu'
import { SIDEBAR_SECTIONS, SETTINGS_NAV } from './nav-config'
import { cn } from '@/lib/utils'

const SIDEBAR_EXPANDED = 240
const SIDEBAR_COLLAPSED = 64

export function Sidebar() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)
  const unreadCount = useUIStore((s) => s.unreadCount)
  const location = useLocation()

  return (
    <TooltipProvider>
      <motion.aside
        animate={{ width: collapsed ? SIDEBAR_COLLAPSED : SIDEBAR_EXPANDED }}
        transition={{ duration: 0.22, ease: [0.25, 0, 0, 1] }}
        className="hidden lg:flex flex-col fixed left-0 top-0 h-full z-30 bg-bg-surface border-r border-chrome/6 overflow-hidden"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <div
          className={cn(
            'flex items-center h-14 border-b border-chrome/6 flex-shrink-0',
            collapsed ? 'justify-center px-0' : 'px-4 gap-2.5'
          )}
        >
          <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-brand-muted border border-brand-border flex-shrink-0">
            <Shield className="w-4 h-4 text-brand" aria-hidden="true" />
            <span
              className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-human"
              aria-hidden="true"
            />
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.18, ease: [0.25, 0, 0, 1] }}
                className="font-semibold text-base text-text-primary tracking-tight whitespace-nowrap overflow-hidden"
              >
                Voice<span className="text-brand">Guard</span>
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* Nav sections */}
        <nav className="flex-1 overflow-y-auto overflow-x-hidden py-4 px-2 space-y-6" aria-label="Sidebar navigation">
          {SIDEBAR_SECTIONS.map((section) => (
            <div key={section.id}>
              {section.label && !collapsed && (
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
                      <Tooltip
                        content={item.label}
                        side="right"
                        disabled={!collapsed}
                      >
                        <NavLink
                          to={item.href}
                          end={item.matchExact}
                          className={cn(
                            'group flex items-center gap-3 rounded-lg px-2.5 py-2.5 text-sm transition-colors duration-150',
                            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                            collapsed && 'justify-center px-0 w-10 h-10 mx-auto',
                            isActive
                              ? item.id === 'new-scan'
                                ? 'bg-brand text-white shadow-glow-brand'
                                : 'bg-brand-muted text-brand'
                              : item.id === 'new-scan'
                              ? 'bg-brand/10 text-brand hover:bg-brand hover:text-white'
                              : 'text-text-secondary hover:bg-chrome/5 hover:text-text-primary'
                          )}
                          aria-current={isActive ? 'page' : undefined}
                          aria-label={collapsed ? item.label : undefined}
                        >
                          <div className="relative flex-shrink-0">
                            <Icon className="w-4.5 h-4.5" aria-hidden="true" />
                            {badge > 0 && (
                              <span
                                className={cn(
                                  'absolute flex items-center justify-center rounded-full bg-brand text-white font-bold',
                                  collapsed
                                    ? '-top-1.5 -right-1.5 w-4 h-4 text-[9px]'
                                    : 'hidden'
                                )}
                                aria-label={`${badge} unread`}
                              >
                                {badge > 9 ? '9+' : badge}
                              </span>
                            )}
                          </div>
                          <AnimatePresence>
                            {!collapsed && (
                              <motion.span
                                initial={{ opacity: 0, width: 0 }}
                                animate={{ opacity: 1, width: 'auto' }}
                                exit={{ opacity: 0, width: 0 }}
                                transition={{ duration: 0.18, ease: [0.25, 0, 0, 1] }}
                                className="flex-1 whitespace-nowrap overflow-hidden flex items-center justify-between"
                              >
                                {item.label}
                                {badge > 0 && (
                                  <span className="ml-auto flex items-center justify-center w-5 h-5 rounded-full bg-brand text-white text-[10px] font-bold">
                                    {badge > 9 ? '9+' : badge}
                                  </span>
                                )}
                              </motion.span>
                            )}
                          </AnimatePresence>
                        </NavLink>
                      </Tooltip>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </nav>

        {/* Bottom: Settings + User */}
        <div className="border-t border-chrome/6 px-2 py-3 space-y-1 flex-shrink-0">
          {/* Settings link */}
          {(() => {
            const Icon = SETTINGS_NAV.icon
            const isActive = location.pathname.startsWith('/settings')
            return (
              <Tooltip content="Settings" side="right" disabled={!collapsed}>
                <NavLink
                  to={SETTINGS_NAV.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-2.5 py-2.5 text-sm transition-colors duration-150',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                    collapsed && 'justify-center px-0 w-10 h-10 mx-auto',
                    isActive
                      ? 'bg-brand-muted text-brand'
                      : 'text-text-secondary hover:bg-chrome/5 hover:text-text-primary'
                  )}
                  aria-current={isActive ? 'page' : undefined}
                  aria-label={collapsed ? 'Settings' : undefined}
                >
                  <Icon className="w-4.5 h-4.5 flex-shrink-0" aria-hidden="true" />
                  <AnimatePresence>
                    {!collapsed && (
                      <motion.span
                        initial={{ opacity: 0, width: 0 }}
                        animate={{ opacity: 1, width: 'auto' }}
                        exit={{ opacity: 0, width: 0 }}
                        transition={{ duration: 0.18, ease: [0.25, 0, 0, 1] }}
                        className="whitespace-nowrap overflow-hidden"
                      >
                        Settings
                      </motion.span>
                    )}
                  </AnimatePresence>
                </NavLink>
              </Tooltip>
            )
          })()}

          {/* User menu */}
          <UserMenu collapsed={collapsed} />

          {/* Collapse toggle */}
          <button
            onClick={toggleSidebar}
            className={cn(
              'w-full flex items-center gap-3 rounded-lg px-2.5 py-2 text-xs text-text-tertiary',
              'hover:bg-chrome/5 hover:text-text-secondary transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
              collapsed && 'justify-center px-0 w-10 h-10 mx-auto'
            )}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <PanelLeft className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
            ) : (
              <>
                <PanelLeftClose className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                <AnimatePresence>
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    transition={{ duration: 0.18, ease: [0.25, 0, 0, 1] }}
                    className="whitespace-nowrap overflow-hidden"
                  >
                    Collapse
                  </motion.span>
                </AnimatePresence>
              </>
            )}
          </button>
        </div>
      </motion.aside>
    </TooltipProvider>
  )
}
