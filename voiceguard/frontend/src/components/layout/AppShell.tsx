import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { MobileDrawer } from './MobileDrawer'
import { NotificationCenter } from './NotificationCenter'
import { GlobalSearch } from './GlobalSearch'
import { useUIStore } from '@/store/uiStore'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import type { BreadcrumbItem } from '@/types'

interface AppShellProps {
  children?: ReactNode
  breadcrumbs?: BreadcrumbItem[]
}

export function AppShell({ children, breadcrumbs }: AppShellProps) {
  const collapsed = useUIStore((s) => s.sidebarCollapsed)
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const paddingLeft = isDesktop ? (collapsed ? 64 : 240) : 0

  return (
    <div className="min-h-screen bg-bg-base">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-brand focus:text-white focus:rounded-lg focus:text-sm focus:font-medium"
      >
        Skip to main content
      </a>

      <Sidebar />
      <MobileDrawer />
      <TopBar breadcrumbs={breadcrumbs} />

      <motion.main
        id="main-content"
        initial={false}
        animate={{ paddingLeft }}
        transition={{ duration: 0.22, ease: [0.25, 0, 0, 1] }}
        className="min-h-screen pt-14"
      >
        {children ?? <Outlet />}
      </motion.main>

      <NotificationCenter />
      <GlobalSearch />
    </div>
  )
}
