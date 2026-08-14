import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export type CardColor = 'brand' | 'human' | 'ai' | 'uncertain' | 'neutral'

interface Trend {
  value: number
  period: string
}

interface StatsCardProps {
  label: string
  value: string | number
  sub?: string
  trend?: Trend
  icon: LucideIcon
  color: CardColor
  loading?: boolean
  index?: number
}

const COLOR_MAP: Record<CardColor, { icon: string; bg: string; border: string }> = {
  brand:    { icon: 'text-brand',    bg: 'bg-brand-muted',    border: 'border-brand-border' },
  human:    { icon: 'text-human',    bg: 'bg-human-muted',    border: 'border-human-border' },
  ai:       { icon: 'text-ai',       bg: 'bg-ai-muted',       border: 'border-ai-border' },
  uncertain:{ icon: 'text-uncertain',bg: 'bg-uncertain-muted',border: 'border-uncertain-border' },
  neutral:  { icon: 'text-text-secondary', bg: 'bg-chrome/5',  border: 'border-chrome/10' },
}

export function StatsCard({
  label,
  value,
  sub,
  trend,
  icon: Icon,
  color,
  loading = false,
  index = 0,
}: StatsCardProps) {
  const colors = COLOR_MAP[color]

  if (loading) {
    return (
      <div className="card-base rounded-xl p-5">
        <div className="flex items-start justify-between mb-4">
          <Skeleton className="w-9 h-9 rounded-lg" />
          <Skeleton className="w-16 h-4 rounded" />
        </div>
        <Skeleton className="w-20 h-7 rounded mb-2" />
        <Skeleton className="w-28 h-3.5 rounded" />
      </div>
    )
  }

  const trendIsPositive = trend && trend.value > 0
  const trendIsNeutral = trend && trend.value === 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.07, ease: [0.25, 0, 0, 1] }}
      className="card-base rounded-xl p-5 group"
    >
      <div className="flex items-start justify-between mb-4">
        <div
          className={cn(
            'w-9 h-9 rounded-lg flex items-center justify-center border flex-shrink-0',
            colors.bg,
            colors.border
          )}
        >
          <Icon className={cn('w-4.5 h-4.5', colors.icon)} aria-hidden="true" />
        </div>

        {trend && (
          <div
            className={cn(
              'flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full',
              trendIsNeutral
                ? 'text-text-tertiary bg-chrome/5'
                : trendIsPositive
                ? 'text-human bg-human-muted border border-human-border'
                : 'text-ai bg-ai-muted border border-ai-border'
            )}
            aria-label={`${trend.value > 0 ? '+' : ''}${trend.value}% ${trend.period}`}
          >
            {trendIsNeutral ? (
              <Minus className="w-3 h-3" aria-hidden="true" />
            ) : trendIsPositive ? (
              <TrendingUp className="w-3 h-3" aria-hidden="true" />
            ) : (
              <TrendingDown className="w-3 h-3" aria-hidden="true" />
            )}
            {Math.abs(trend.value)}%
          </div>
        )}
      </div>

      <div
        className={cn('text-2xl font-bold text-text-primary tabular-nums mb-1', colors.icon)}
        aria-label={`${label}: ${value}`}
      >
        {value}
      </div>
      <p className="text-sm font-medium text-text-secondary">{label}</p>
      {sub && <p className="text-xs text-text-tertiary mt-0.5">{sub}</p>}
    </motion.div>
  )
}
