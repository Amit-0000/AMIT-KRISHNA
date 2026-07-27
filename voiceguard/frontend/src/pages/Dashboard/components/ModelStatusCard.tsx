import { motion } from 'framer-motion'
import { Cpu, CheckCircle2, AlertTriangle, XCircle, ExternalLink } from 'lucide-react'
import { formatRelativeTime } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import type { ModelStatus, ModelHealth } from '../types'

const HEALTH_CONFIG: Record<
  ModelHealth,
  { label: string; icon: typeof CheckCircle2; iconClass: string; badgeClass: string }
> = {
  healthy:  { label: 'Healthy',  icon: CheckCircle2,  iconClass: 'text-human',     badgeClass: 'text-human bg-human-muted border-human-border' },
  degraded: { label: 'Degraded', icon: AlertTriangle, iconClass: 'text-uncertain',  badgeClass: 'text-uncertain bg-uncertain-muted border-uncertain-border' },
  down:     { label: 'Down',     icon: XCircle,       iconClass: 'text-ai',         badgeClass: 'text-ai bg-ai-muted border-ai-border' },
}

interface ModelStatusCardProps {
  status: ModelStatus | undefined
  loading?: boolean
}

export function ModelStatusCard({ status, loading = false }: ModelStatusCardProps) {
  const health = status?.health ?? 'healthy'
  const cfg = HEALTH_CONFIG[health]
  const HealthIcon = cfg.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.12, ease: [0.25, 0, 0, 1] }}
      className="card-base rounded-xl overflow-hidden"
    >
      <div className="px-4 py-3.5 border-b border-white/6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-brand" aria-hidden="true" />
          <h2 className="text-heading-sm font-semibold text-text-primary">Model Status</h2>
        </div>
        {!loading && status && (
          <span
            className={cn(
              'inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider px-2 py-1 rounded-full border',
              cfg.badgeClass
            )}
            aria-label={`Model health: ${cfg.label}`}
          >
            <HealthIcon className="w-3 h-3" aria-hidden="true" />
            {cfg.label}
          </span>
        )}
      </div>

      <div className="px-4 py-4 space-y-3">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex justify-between items-center">
              <Skeleton className="w-24 h-3.5 rounded" />
              <Skeleton className="w-16 h-3.5 rounded" />
            </div>
          ))
        ) : status ? (
          <>
            {[
              { label: 'Version',       value: status.version },
              { label: 'EER',           value: `${status.eer_pct}%` },
              { label: 'Avg inference', value: `${status.avg_inference_ms}ms` },
              { label: 'Uptime',        value: `${status.uptime_pct}%` },
              { label: 'Parameters',    value: status.parameters.toLocaleString() },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between gap-3">
                <span className="text-xs text-text-tertiary">{label}</span>
                <span className="text-xs font-semibold text-text-primary font-mono">{value}</span>
              </div>
            ))}
            <div className="pt-2 border-t border-white/6">
              <p className="text-[10px] text-text-tertiary">
                Last checked {formatRelativeTime(status.last_checked)}
              </p>
            </div>
          </>
        ) : null}
      </div>

      <a
        href="https://arxiv.org/abs/1901.09394"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 px-4 py-3 border-t border-white/6 text-xs text-text-tertiary hover:text-text-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand"
        aria-label="LCNN paper (opens in new tab)"
      >
        <ExternalLink className="w-3 h-3" aria-hidden="true" />
        LCNN paper · ASVspoof 2019
      </a>
    </motion.div>
  )
}
