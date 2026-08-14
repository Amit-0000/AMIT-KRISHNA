import { motion } from 'framer-motion'
import { Menu, Search, Bell } from 'lucide-react'
import { useUIStore } from '@/store/uiStore'
import { Breadcrumb } from './Breadcrumb'
import { ThemeToggle } from './ThemeToggle'
import { Tooltip, TooltipProvider } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import type { BreadcrumbItem } from '@/types'

interface TopBarProps {
  breadcrumbs?: BreadcrumbItem[]
}

export function TopBar({ breadcrumbs }: TopBarProps) {
  const collapsed = useUIStore((s) => s.sidebarCollapsed)
  const setMobileDrawerOpen = useUIStore((s) => s.setMobileDrawerOpen)
  const setSearchOpen = useUIStore((s) => s.setSearchOpen)
  const setNotificationOpen = useUIStore((s) => s.setNotificationPanelOpen)
  const notifOpen = useUIStore((s) => s.notificationPanelOpen)
  const unreadCount = useUIStore((s) => s.unreadCount)

  const sidebarWidth = collapsed ? 64 : 240

  return (
    <TooltipProvider>
      <motion.header
        animate={{ paddingLeft: sidebarWidth }}
        transition={{ duration: 0.22, ease: [0.25, 0, 0, 1] }}
        className="fixed top-0 right-0 left-0 z-20 h-14 flex items-center bg-bg-base/90 backdrop-blur-sm border-b border-chrome/6"
        role="banner"
      >
        <div className="flex items-center gap-3 w-full px-4">
          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileDrawerOpen(true)}
            className="lg:hidden flex items-center justify-center w-9 h-9 rounded-lg text-text-secondary hover:text-text-primary hover:bg-chrome/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            aria-label="Open navigation"
            aria-expanded={false}
            aria-controls="mobile-nav"
          >
            <Menu className="w-5 h-5" aria-hidden="true" />
          </button>

          {/* Breadcrumb */}
          <Breadcrumb overrides={breadcrumbs} className="flex-1 min-w-0 hidden sm:flex" />
          <div className="flex-1 sm:hidden" />

          {/* Right actions */}
          <div className="flex items-center gap-1 ml-auto">
            {/* Search trigger */}
            <Tooltip content="Search (⌘K)" side="bottom">
              <button
                onClick={() => setSearchOpen(true)}
                className={cn(
                  'hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-text-tertiary',
                  'border border-chrome/8 bg-chrome/3 hover:bg-chrome/6 hover:text-text-secondary',
                  'transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand'
                )}
                aria-label="Search (Command K)"
              >
                <Search className="w-3.5 h-3.5" aria-hidden="true" />
                <span className="hidden md:block">Search…</span>
                <span className="hidden md:block text-[10px] font-medium px-1.5 py-0.5 rounded border border-chrome/10 font-mono">
                  ⌘K
                </span>
              </button>
            </Tooltip>

            {/* Mobile search icon */}
            <button
              onClick={() => setSearchOpen(true)}
              className="sm:hidden flex items-center justify-center w-9 h-9 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-chrome/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
              aria-label="Search"
            >
              <Search className="w-4.5 h-4.5" aria-hidden="true" />
            </button>

            {/* Theme toggle */}
            <ThemeToggle variant="icon" />

            {/* Notification bell */}
            <Tooltip content="Notifications" side="bottom">
              <button
                onClick={() => setNotificationOpen(!notifOpen)}
                className={cn(
                  'relative flex items-center justify-center w-9 h-9 rounded-lg transition-colors duration-150',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                  notifOpen
                    ? 'bg-brand-muted text-brand'
                    : 'text-text-tertiary hover:text-text-primary hover:bg-chrome/5'
                )}
                aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
                aria-pressed={notifOpen}
              >
                <Bell className="w-4.5 h-4.5" aria-hidden="true" />
                {unreadCount > 0 && (
                  <span
                    className="absolute top-1 right-1 flex items-center justify-center w-4 h-4 rounded-full bg-brand text-white text-[9px] font-bold"
                    aria-hidden="true"
                  >
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </button>
            </Tooltip>
          </div>
        </div>
      </motion.header>
    </TooltipProvider>
  )
}
