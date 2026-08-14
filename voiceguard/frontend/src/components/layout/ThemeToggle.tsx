import { Sun, Moon, Monitor } from 'lucide-react'
import { useUIStore } from '@/store/uiStore'
import { Tooltip } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import type { Theme } from '@/types'

const OPTIONS: { value: Theme; icon: typeof Sun; label: string }[] = [
  { value: 'light', icon: Sun, label: 'Light mode' },
  { value: 'system', icon: Monitor, label: 'System theme' },
  { value: 'dark', icon: Moon, label: 'Dark mode' },
]

interface ThemeToggleProps {
  variant?: 'icon' | 'cycle'
}

export function ThemeToggle({ variant = 'cycle' }: ThemeToggleProps) {
  const theme = useUIStore((s) => s.theme)
  const setTheme = useUIStore((s) => s.setTheme)

  if (variant === 'icon') {
    const current = OPTIONS.find((o) => o.value === theme) ?? OPTIONS[2]
    const Icon = current.icon

    const cycle = () => {
      const idx = OPTIONS.findIndex((o) => o.value === theme)
      const next = OPTIONS[(idx + 1) % OPTIONS.length]
      setTheme(next.value)
    }

    return (
      <Tooltip content={current.label} side="bottom">
        <button
          onClick={cycle}
          className="flex items-center justify-center w-9 h-9 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-chrome/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          aria-label={`Current theme: ${current.label}. Click to cycle.`}
        >
          <Icon className="w-4.5 h-4.5" aria-hidden="true" />
        </button>
      </Tooltip>
    )
  }

  return (
    <div
      className="flex items-center gap-1 p-1 rounded-lg bg-bg-base border border-chrome/8"
      role="radiogroup"
      aria-label="Color theme"
    >
      {OPTIONS.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          role="radio"
          aria-checked={theme === value}
          aria-label={label}
          onClick={() => setTheme(value)}
          className={cn(
            'flex items-center justify-center w-8 h-8 rounded-md transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
            theme === value
              ? 'bg-brand-muted text-brand'
              : 'text-text-tertiary hover:text-text-secondary hover:bg-chrome/5'
          )}
        >
          <Icon className="w-4 h-4" aria-hidden="true" />
        </button>
      ))}
    </div>
  )
}
