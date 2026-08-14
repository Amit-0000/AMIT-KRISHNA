import { Sun, Moon, Monitor, PanelLeft, PanelLeftClose, Accessibility } from 'lucide-react'
import { SettingsLayout } from './SettingsLayout'
import { useUIStore } from '@/store/uiStore'
import { useReducedMotion } from '@/hooks/useReducedMotion'
import { cn } from '@/lib/utils'
import type { Theme } from '@/types'

const THEME_OPTIONS: { value: Theme; icon: typeof Sun; label: string; description: string }[] = [
  { value: 'light', icon: Sun, label: 'Light', description: 'Bright background, dark text' },
  { value: 'dark', icon: Moon, label: 'Dark', description: 'Low-light, high-contrast interface' },
  { value: 'system', icon: Monitor, label: 'System', description: 'Match your OS setting' },
]

export function AppearancePage() {
  const theme = useUIStore((s) => s.theme)
  const setTheme = useUIStore((s) => s.setTheme)
  const sidebarCollapsed = useUIStore((s) => s.sidebarCollapsed)
  const setSidebarCollapsed = useUIStore((s) => s.setSidebarCollapsed)
  const prefersReducedMotion = useReducedMotion()

  return (
    <SettingsLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-heading-lg font-semibold text-text-primary">Appearance</h2>
          <p className="text-sm text-text-secondary mt-1">
            Control how VoiceGuard looks and feels on this device.
          </p>
        </div>

        {/* Theme */}
        <div className="card-base rounded-xl p-6">
          <h3 className="text-sm font-semibold text-text-primary mb-1">Theme</h3>
          <p className="text-xs text-text-tertiary mb-4">
            Choose Light, Dark, or System to match your OS. Your preference is saved to this device and
            applied everywhere in VoiceGuard.
          </p>
          <div
            role="radiogroup"
            aria-label="Theme"
            className="grid grid-cols-1 sm:grid-cols-3 gap-3"
          >
            {THEME_OPTIONS.map(({ value, icon: Icon, label, description }) => {
              const active = theme === value
              return (
                <button
                  key={value}
                  role="radio"
                  aria-checked={active}
                  onClick={() => setTheme(value)}
                  className={cn(
                    'flex flex-col items-start gap-2 rounded-xl border p-4 text-left transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                    active
                      ? 'border-brand/50 bg-brand-muted'
                      : 'border-chrome/8 bg-chrome/[0.02] hover:bg-chrome/5 hover:border-chrome/15'
                  )}
                >
                  <Icon className={cn('w-5 h-5', active ? 'text-brand' : 'text-text-tertiary')} aria-hidden="true" />
                  <div>
                    <p className={cn('text-sm font-medium', active ? 'text-brand' : 'text-text-primary')}>
                      {label}
                    </p>
                    <p className="text-xs text-text-tertiary mt-0.5">{description}</p>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Layout density */}
        <div className="card-base rounded-xl p-6">
          <h3 className="text-sm font-semibold text-text-primary mb-1">Navigation</h3>
          <p className="text-xs text-text-tertiary mb-4">
            Choose how much space the sidebar takes on larger screens.
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarCollapsed(false)}
              aria-pressed={!sidebarCollapsed}
              className={cn(
                'flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                !sidebarCollapsed
                  ? 'border-brand/50 bg-brand-muted text-brand'
                  : 'border-chrome/8 text-text-secondary hover:bg-chrome/5'
              )}
            >
              <PanelLeft className="w-4 h-4" aria-hidden="true" />
              Expanded
            </button>
            <button
              onClick={() => setSidebarCollapsed(true)}
              aria-pressed={sidebarCollapsed}
              className={cn(
                'flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                sidebarCollapsed
                  ? 'border-brand/50 bg-brand-muted text-brand'
                  : 'border-chrome/8 text-text-secondary hover:bg-chrome/5'
              )}
            >
              <PanelLeftClose className="w-4 h-4" aria-hidden="true" />
              Compact
            </button>
          </div>
        </div>

        {/* Motion */}
        <div className="card-base rounded-xl p-6">
          <div className="flex items-start gap-3">
            <Accessibility className="w-5 h-5 text-text-tertiary flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-1">Motion</h3>
              <p className="text-xs text-text-tertiary">
                {prefersReducedMotion
                  ? "Reduced motion is on — VoiceGuard is honoring your operating system's accessibility setting and toning down animated sections."
                  : 'VoiceGuard follows your operating system\'s "reduce motion" accessibility setting automatically wherever animation is decorative. Enable it in your OS to tone down animated sections here.'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </SettingsLayout>
  )
}
