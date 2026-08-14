import { type ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { PageContainer } from '@/components/layout/PageContainer'
import { SETTINGS_ITEMS } from '@/components/layout/nav-config'
import { cn } from '@/lib/utils'

interface SettingsLayoutProps {
  children: ReactNode
}

export function SettingsLayout({ children }: SettingsLayoutProps) {
  return (
    <PageContainer
      maxWidth="lg"
      title="Settings"
      description="Manage your profile, account, and how VoiceGuard looks."
    >
      <div className="flex flex-col md:flex-row gap-6 md:gap-10">
        {/* Tabs — horizontal on mobile, vertical sidebar on desktop */}
        <nav
          aria-label="Settings sections"
          className="flex md:flex-col gap-1 overflow-x-auto md:overflow-visible md:w-48 flex-shrink-0 -mx-1 px-1 md:mx-0 md:px-0"
        >
          {SETTINGS_ITEMS.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.id}
                to={item.href}
                end={item.matchExact}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium whitespace-nowrap transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                    isActive
                      ? 'bg-brand-muted text-brand'
                      : 'text-text-secondary hover:bg-chrome/5 hover:text-text-primary'
                  )
                }
              >
                <Icon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                {item.label}
              </NavLink>
            )
          })}
        </nav>

        <div className="flex-1 min-w-0">{children}</div>
      </div>
    </PageContainer>
  )
}
