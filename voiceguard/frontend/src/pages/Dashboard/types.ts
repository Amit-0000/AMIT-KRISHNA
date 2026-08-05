import type { Verdict, ScanResult } from '@/types'

// ─── Stats ────────────────────────────────────────────────────────────────────

export interface DashboardStats {
  total_scans: number
  ai_detected: number
  human_verified: number
  uncertain: number
  avg_processing_ms: number
  scans_today: number
  scan_limit_daily: number
  reset_in_hours: number
}

// ─── Trend ───────────────────────────────────────────────────────────────────

export interface TrendDataPoint {
  date: string       // "Jan 15"
  total: number
  ai_generated: number
  human: number
  uncertain: number
}

// ─── Confidence distribution ─────────────────────────────────────────────────

export interface ConfidenceBucket {
  range: string      // "0–10%"
  min: number
  max: number
  count: number
  zone: 'uncertain' | 'borderline' | 'definitive'
}

// ─── Activity ────────────────────────────────────────────────────────────────

export type ActivityType =
  | 'scan_complete'
  | 'scan_failed'
  | 'feedback_submitted'
  | 'model_updated'
  | 'account_created'

export interface ActivityItem {
  id: string
  type: ActivityType
  title: string
  description: string
  timestamp: string
  verdict?: Verdict
  scan_id?: string
}

// ─── Model status ─────────────────────────────────────────────────────────────

export type ModelHealth = 'healthy' | 'degraded' | 'down'

// eer_pct/avg_inference_ms/uptime_pct/parameters are optional: the backend
// only populates what it can genuinely measure at serve time (there's no
// uptime-monitoring subsystem or offline EER tracking wired up yet) — see
// api/dashboard/schemas.py's ModelStatusResponse docstring. ModelStatusCard
// skips rendering a stat row when its value is undefined rather than
// showing a fabricated number.
export interface ModelStatus {
  version: string
  health: ModelHealth
  eer_pct?: number
  avg_inference_ms?: number
  last_checked: string
  uptime_pct?: number
  parameters?: number
}

// ─── Dashboard aggregate ──────────────────────────────────────────────────────

export interface DashboardData {
  stats: DashboardStats
  trend: TrendDataPoint[]
  confidence_distribution: ConfidenceBucket[]
  recent_activity: ActivityItem[]
  model_status: ModelStatus
}

// ─── Recent scans table ───────────────────────────────────────────────────────

export type SortField = 'file_name' | 'verdict' | 'confidence' | 'created_at' | 'inference_time_ms'
export type SortDir = 'asc' | 'desc'

export interface RecentScansState {
  search: string
  sortBy: SortField
  sortDir: SortDir
  page: number
  pageSize: number
}

export type { ScanResult }
