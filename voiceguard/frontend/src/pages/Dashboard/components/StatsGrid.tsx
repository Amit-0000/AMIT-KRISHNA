import { Scan, AlertTriangle, CheckCircle2, Zap } from 'lucide-react'
import { StatsCard } from './StatsCard'
import type { DashboardStats } from '../types'

interface StatsGridProps {
  stats: DashboardStats | undefined
  loading?: boolean
}

export function StatsGrid({ stats, loading = false }: StatsGridProps) {
  const aiPct = stats && stats.total_scans > 0
    ? Math.round((stats.ai_detected / stats.total_scans) * 100)
    : 0
  const humanPct = stats && stats.total_scans > 0
    ? Math.round((stats.human_verified / stats.total_scans) * 100)
    : 0

  return (
    <div
      className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6"
      role="region"
      aria-label="Summary statistics"
    >
      <StatsCard
        index={0}
        label="Total Analyses"
        value={loading ? '—' : (stats?.total_scans ?? 0).toLocaleString()}
        sub="All time"
        icon={Scan}
        color="brand"
        loading={loading}
        trend={loading ? undefined : { value: 12, period: 'vs last week' }}
      />
      <StatsCard
        index={1}
        label="AI Detected"
        value={loading ? '—' : `${stats?.ai_detected ?? 0}`}
        sub={loading ? undefined : `${aiPct}% of total`}
        icon={AlertTriangle}
        color="ai"
        loading={loading}
        trend={loading ? undefined : { value: 8, period: 'vs last week' }}
      />
      <StatsCard
        index={2}
        label="Human Verified"
        value={loading ? '—' : `${stats?.human_verified ?? 0}`}
        sub={loading ? undefined : `${humanPct}% of total`}
        icon={CheckCircle2}
        color="human"
        loading={loading}
        trend={loading ? undefined : { value: 5, period: 'vs last week' }}
      />
      <StatsCard
        index={3}
        label="Avg Processing"
        value={loading ? '—' : `${stats?.avg_processing_ms ?? 0}ms`}
        sub="Per segment"
        icon={Zap}
        color="neutral"
        loading={loading}
        trend={loading ? undefined : { value: -3, period: 'vs last week' }}
      />
    </div>
  )
}
