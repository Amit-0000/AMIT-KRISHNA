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

// ─── Scan lifecycle (Audio Upload & Scan Management) ──────────────────────────
// Distinct from ScanResult/ScanStatus above: those model the future
// AI-inference result (verdict, confidence, ...), which this slice does not
// produce. ScanRecord mirrors api.scans.schemas.ScanResponse exactly — the
// scan's lifecycle up to READY_FOR_AI, before any AI analysis exists.

export type ScanRecordStatus =
  | 'created'
  | 'validating'
  | 'uploading'
  | 'queued'
  | 'preprocessing'
  | 'ready_for_ai'
  // ── AI Processing Pipeline (Vertical Slice 03) ────────────────────────────
  | 'preparing_model'
  | 'loading_model'
  | 'ai_preprocessing'
  | 'feature_extraction'
  | 'running_inference'
  | 'postprocessing'
  | 'generating_explanation'
  | 'saving_results'
  | 'completed'
  | 'failed'
  | 'validation_failed'
  | 'upload_failed'
  | 'cancelled'
  | 'expired'
  | 'model_load_failed'
  | 'ai_preprocessing_failed'
  | 'feature_extraction_failed'
  | 'inference_failed'
  | 'postprocessing_failed'
  | 'result_persistence_failed'

// "clean" | "malicious" | "unavailable" | "not_scanned" — mirrors
// api.scans.malware_scan.MalwareScanRecordStatus. null only for a scan that
// hasn't reached the malware-scan step yet, or predates this field.
// Deliberately never conflated with a "safe" claim: "not_scanned" means the
// AI pipeline ran without a malware verdict, not that the file was cleared.
export type MalwareScanRecordStatus = 'clean' | 'malicious' | 'unavailable' | 'not_scanned'

export interface ScanRecord {
  id: string
  status: ScanRecordStatus
  original_filename: string
  file_extension: string
  declared_mime_type: string | null
  file_size_bytes: number
  sha256_checksum: string
  duration_seconds: number | null
  scan_metadata: Record<string, unknown> | null
  malware_scan_status: MalwareScanRecordStatus | null
  error_code: string | null
  error_message: string | null
  retry_count: number
  created_at: string
  updated_at: string
  queued_at: string | null
  preprocessing_started_at: string | null
  ready_at: string | null
  completed_at: string | null
  failed_at: string | null
  cancelled_at: string | null
  expires_at: string | null
}

export interface ScanRecordStatusOnly {
  id: string
  status: ScanRecordStatus
  error_code: string | null
  error_message: string | null
  updated_at: string
}

export interface ScanListMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

// ─── AI Processing Pipeline result (Vertical Slice 03) ─────────────────────────
// Distinct from `ScanResult`/`Verdict` above: those were scaffolded ahead of
// this slice and now back the real GET /dashboard and GET
// /dashboard/recent-scans endpoints (frontend/src/pages/Dashboard). These
// mirror api.inference.schemas' actual response shapes for GET
// /scans/{id}/result|technical|explanation instead.

export type AIVerdict = 'human' | 'ai_generated' | 'uncertain'

export interface AIScanResult {
  scan_id: string
  verdict: AIVerdict
  confidence: number
  model_version: string
  processing_time_ms: number
  inference_time_ms: number
  created_at: string
  // Deliberately separate from `verdict` — the AI's opinion about the audio
  // and whether the file was actually malware-scanned are independent facts.
  malware_scan_status: MalwareScanRecordStatus | null
}

export interface StageTiming {
  stage: string
  attempt: number
  status: 'succeeded' | 'failed'
  duration_ms: number
}

export interface AIScanTechnical {
  scan_id: string
  label: 'bonafide' | 'spoof'
  verdict: AIVerdict
  confidence: number
  raw_bonafide_score: number
  raw_spoof_score: number
  threshold_used: number
  is_below_threshold: boolean
  feature_extractor_name: string
  feature_extractor_version: string
  model_name: string
  model_version: string
  model_architecture: string
  processing_time_ms: number
  inference_time_ms: number
  stage_timings: StageTiming[]
  created_at: string
}

export interface SalientRegion {
  start_s: number
  end_s: number
  importance: number
}

export interface AIScanExplanation {
  scan_id: string
  salient_regions: SalientRegion[]
  notes: string[]
  warnings: string[]
  feature_extractor: string
  model_version: string
}

export interface ModelVersionInfo {
  id: string
  name: string
  version: string
  architecture: string
  status: 'active' | 'inactive' | 'deprecated'
  feature_extractor_name: string
  feature_extractor_version: string
  loaded_at: string | null
  created_at: string
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

export interface ApiErrorDetail {
  field?: string
  message: string
}

export interface ApiError {
  code: string
  message: string
  field?: string
  retry_after?: number
  details?: ApiErrorDetail[]
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
