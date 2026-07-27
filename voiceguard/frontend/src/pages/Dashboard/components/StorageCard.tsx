import { motion } from 'framer-motion'
import { BarChart2, RefreshCw } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import type { DashboardStats } from '../types'

interface StorageCardProps {
  stats: DashboardStats | undefined
  loading?: boolean
}

export function StorageCard({ stats, loading = false }: StorageCardProps) {
  const used = stats?.scans_today ?? 0
  const limit = stats?.scan_limit_daily ?? 50
  const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0
  const remaining = Math.max(0, limit - used)
  const resetHours = stats?.reset_in_hours ?? 0

  const barColor =
    pct >= 90 ? 'bg-ai'
    : pct >= 70 ? 'bg-uncertain'
    : 'bg-brand'

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.16, ease: [0.25, 0, 0, 1] }}
      className="card-base rounded-xl p-4"
    >
      <div className="flex items-center gap-2 mb-4">
        <BarChart2 className="w-4 h-4 text-brand" aria-hidden="true" />
        <h2 className="text-heading-sm font-semibold text-text-primary">Daily Usage</h2>
      </div>

      {loading ? (
        <div className="space-y-3">
          <Skeleton className="w-full h-2 rounded-full" />
          <Skeleton className="w-1/2 h-3.5 rounded" />
          <Skeleton className="w-3/4 h-3.5 rounded" />
        </div>
      ) : (
        <>
          {/* Progress bar */}
          <div
            className="w-full h-2 rounded-full bg-white/8 overflow-hidden mb-2"
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Daily scan usage: ${used} of ${limit}`}
          >
            <motion.div
              className={cn('h-full rounded-full', barColor)}
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 0.8, delay: 0.3, ease: [0.25, 0, 0, 1] }}
            />
          </div>

          <div className="flex items-center justify-between mb-3">
            <span className="text-xs text-text-secondary">
              <span className="font-semibold text-text-primary">{used}</span> / {limit} scans today
            </span>
            <span className="text-xs text-text-tertiary tabular-nums">{pct}%</span>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-text-tertiary">
            <RefreshCw className="w-3 h-3" aria-hidden="true" />
            {remaining > 0
              ? `${remaining} remaining · resets in ${resetHours}h`
              : `Limit reached · resets in ${resetHours}h`}
          </div>
        </>
      )}
    </motion.div>
  )
}
