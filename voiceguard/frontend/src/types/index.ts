// ─── Verdict ────────────────────────────────────────────────────────────────

export type Verdict = 'human' | 'ai_generated' | 'uncertain'

export interface VerdictInfo {
  verdict: Verdict
  label: string
  color: string
  bgColor: string
  borderColor: string
  description: string
}

// ─── User & Auth ─────────────────────────────────────────────────────────────

export type AuthProvider = 'email' | 'google' | 'github'
export type UserRole = 'guest' | 'user' | 'admin'
export type SubscriptionTier = 'free' | 'pro' | 'enterprise'

export interface User {
  id: string
  email: string
  display_name: string
  avatar_url: string | null
  role: UserRole
  subscription_tier: SubscriptionTier
  email_verified: boolean
  onboarding_completed: boolean
  created_at: string
  scan_count_today: number
  scan_limit_daily: number
}

export interface GuestSession {
  token: string
  expires_at: string
  scans_remaining: number
}

// ─── Scan ─────────────────────────────────────────────────────────────────────

export type ScanStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface ScanResult {
  scan_id: string
  status: ScanStatus
  verdict: Verdict
  confidence: number
  human_score: number
  ai_score: number
  inference_time_ms: number
  model_version: string
  segment_count: number
  frequency_heatmap: string | null
  file_name: string
  file_duration_seconds: number
  created_at: string
  share_token: string | null
  user_verdict: Verdict | null
}

export interface ScanProcessingUpdate {
  scan_id: string
  status: ScanStatus
  progress_pct: number
  current_step: string
  error_code?: string
  error_message?: string
}

// ─── Notifications ────────────────────────────────────────────────────────────

export type NotificationType =
  | 'scan_complete'
  | 'scan_failed'
  | 'system'
  | 'alert'
  | 'info'
  | 'feedback_thanks'

export interface AppNotification {
  id: string
  type: NotificationType
  title: string
  body: string
  read: boolean
  created_at: string
  action_url?: string
  meta?: Record<string, string>
}

// ─── API ─────────────────────────────────────────────────────────────────────

export interface ApiError {
  code: string
  message: string
  field?: string
  retry_after?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

// ─── UI ──────────────────────────────────────────────────────────────────────

export type Theme = 'dark' | 'light' | 'system'

export interface Toast {
  id: string
  title: string
  description?: string
  variant: 'default' | 'success' | 'error' | 'warning'
  duration?: number
}

export interface NavItem {
  label: string
  href: string
  icon?: string
  badge?: string
  requiresAuth?: boolean
}

export interface BreadcrumbItem {
  label: string
  href?: string
}

export type SidebarWidth = 'expanded' | 'collapsed'

// ─── Search ──────────────────────────────────────────────────────────────────

export type SearchResultType = 'scan' | 'nav' | 'help' | 'action'

export interface SearchResult {
  id: string
  type: SearchResultType
  label: string
  description?: string
  href: string
  icon?: string
  verdict?: Verdict
  timestamp?: string
}

// ─── Landing Page ─────────────────────────────────────────────────────────────

export interface Testimonial {
  id: string
  quote: string
  author: string
  role: string
  organization: string
  avatar?: string
}

export interface UseCase {
  id: string
  icon: string
  title: string
  description: string
  audience: string
}

export interface TechSpec {
  label: string
  value: string
  description?: string
}
