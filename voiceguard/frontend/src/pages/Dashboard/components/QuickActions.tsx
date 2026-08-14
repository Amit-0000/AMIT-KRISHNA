import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Upload,
  Clock,
  HelpCircle,
  MessageSquare,
  ChevronRight,
  Share2,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ActionItem {
  label: string
  description: string
  href: string
  icon: LucideIcon
  primary?: boolean
}

const ACTIONS: ActionItem[] = [
  {
    label: 'Analyze Audio',
    description: 'Upload and detect deepfakes',
    href: '/scan/new',
    icon: Upload,
    primary: true,
  },
  {
    label: 'View History',
    description: 'All past scan results',
    href: '/history',
    icon: Clock,
  },
  {
    label: 'Share a Result',
    description: 'Open a past scan to generate its link',
    href: '/history',
    icon: Share2,
  },
  {
    label: 'Help Center',
    description: 'Guides and documentation',
    href: '/help',
    icon: HelpCircle,
  },
  {
    label: 'Give Feedback',
    description: 'Report issues or suggest improvements',
    href: '/feedback',
    icon: MessageSquare,
  },
]

export function QuickActions() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.08, ease: [0.25, 0, 0, 1] }}
      className="card-base rounded-xl overflow-hidden"
    >
      <div className="px-4 py-3.5 border-b border-chrome/6">
        <h2 className="text-heading-sm font-semibold text-text-primary">Quick Actions</h2>
      </div>
      <ul role="list" className="divide-y divide-chrome/4">
        {ACTIONS.map((action) => {
          const Icon = action.icon
          return (
            <li key={action.href + action.label}>
              <Link
                to={action.href}
                className={cn(
                  'flex items-center gap-3 px-4 py-3 transition-colors group',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand',
                  action.primary
                    ? 'hover:bg-brand-muted/40'
                    : 'hover:bg-chrome/3'
                )}
              >
                <div
                  className={cn(
                    'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center border transition-colors',
                    action.primary
                      ? 'bg-brand-muted border-brand-border text-brand group-hover:bg-brand group-hover:text-white group-hover:border-brand'
                      : 'bg-chrome/5 border-chrome/8 text-text-secondary group-hover:text-text-primary'
                  )}
                >
                  <Icon className="w-4 h-4" aria-hidden="true" />
                </div>
                <div className="flex-1 min-w-0">
                  <p
                    className={cn(
                      'text-sm font-medium leading-tight',
                      action.primary ? 'text-brand group-hover:text-white' : 'text-text-primary'
                    )}
                  >
                    {action.label}
                  </p>
                  <p className="text-xs text-text-tertiary truncate">{action.description}</p>
                </div>
                <ChevronRight
                  className="w-3.5 h-3.5 text-text-tertiary group-hover:text-text-secondary flex-shrink-0 transition-transform group-hover:translate-x-0.5"
                  aria-hidden="true"
                />
              </Link>
            </li>
          )
        })}
      </ul>
    </motion.div>
  )
}
