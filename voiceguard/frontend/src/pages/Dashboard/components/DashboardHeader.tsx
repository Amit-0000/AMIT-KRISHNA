import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Upload, ChevronRight, CalendarDays } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { User } from '@/types'

function getGreeting(): string {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

function formatToday(): string {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date())
}

interface DashboardHeaderProps {
  user: User | null
  scansToday: number
  dailyLimit: number
}

export function DashboardHeader({ user, scansToday, dailyLimit }: DashboardHeaderProps) {
  const firstName = user?.display_name?.split(' ')[0] ?? 'there'
  const remaining = Math.max(0, dailyLimit - scansToday)

  return (
    <motion.div
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.25, 0, 0, 1] }}
      className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8"
    >
      <div>
        <div className="flex items-center gap-2 mb-1">
          <CalendarDays className="w-3.5 h-3.5 text-text-tertiary" aria-hidden="true" />
          <span className="text-xs text-text-tertiary">{formatToday()}</span>
        </div>
        <h1 className="text-display-sm font-bold text-text-primary">
          {getGreeting()},{' '}
          <span className="text-gradient-brand">{firstName}</span>
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          {remaining > 0
            ? `${remaining} of ${dailyLimit} scans remaining today`
            : 'Daily scan limit reached — resets at midnight'}
        </p>
      </div>

      <div className="flex items-center gap-3 flex-shrink-0">
        <Link to="/scan/new">
          <Button size="lg" className="gap-2 group">
            <Upload
              className="w-4 h-4 transition-transform group-hover:-translate-y-0.5"
              aria-hidden="true"
            />
            Analyze Audio
            <ChevronRight
              className="w-4 h-4 transition-transform group-hover:translate-x-0.5"
              aria-hidden="true"
            />
          </Button>
        </Link>
      </div>
    </motion.div>
  )
}
