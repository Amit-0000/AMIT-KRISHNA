import { CheckCircle2, Clock, Loader2, UploadCloud, XCircle, AlertTriangle } from 'lucide-react'
import { Badge, type BadgeProps } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { ScanRecordStatus } from '@/types'

const STATUS_CONFIG: Record<
  ScanRecordStatus,
  { label: string; variant: NonNullable<BadgeProps['variant']>; icon: typeof CheckCircle2; spin?: boolean }
> = {
  created: { label: 'Uploading', variant: 'neutral', icon: UploadCloud },
  validating: { label: 'Validating', variant: 'neutral', icon: Loader2, spin: true },
  uploading: { label: 'Uploading', variant: 'neutral', icon: UploadCloud },
  queued: { label: 'Queued', variant: 'neutral', icon: Clock },
  preprocessing: { label: 'Processing', variant: 'default', icon: Loader2, spin: true },
  ready_for_ai: { label: 'Ready for AI', variant: 'success', icon: CheckCircle2 },
  // ── AI Processing Pipeline (Vertical Slice 03) ────────────────────────────
  preparing_model: { label: 'Preparing model', variant: 'default', icon: Loader2, spin: true },
  loading_model: { label: 'Loading model', variant: 'default', icon: Loader2, spin: true },
  ai_preprocessing: { label: 'Analyzing audio', variant: 'default', icon: Loader2, spin: true },
  feature_extraction: { label: 'Extracting features', variant: 'default', icon: Loader2, spin: true },
  running_inference: { label: 'Running detection', variant: 'default', icon: Loader2, spin: true },
  postprocessing: { label: 'Scoring confidence', variant: 'default', icon: Loader2, spin: true },
  generating_explanation: { label: 'Generating explanation', variant: 'default', icon: Loader2, spin: true },
  saving_results: { label: 'Saving results', variant: 'default', icon: Loader2, spin: true },
  completed: { label: 'Completed', variant: 'success', icon: CheckCircle2 },
  failed: { label: 'Failed', variant: 'error', icon: AlertTriangle },
  validation_failed: { label: 'Rejected', variant: 'error', icon: AlertTriangle },
  upload_failed: { label: 'Upload failed', variant: 'error', icon: AlertTriangle },
  cancelled: { label: 'Cancelled', variant: 'neutral', icon: XCircle },
  expired: { label: 'Expired', variant: 'warning', icon: Clock },
  model_load_failed: { label: 'Model unavailable', variant: 'error', icon: AlertTriangle },
  ai_preprocessing_failed: { label: 'Analysis failed', variant: 'error', icon: AlertTriangle },
  feature_extraction_failed: { label: 'Analysis failed', variant: 'error', icon: AlertTriangle },
  inference_failed: { label: 'Detection failed', variant: 'error', icon: AlertTriangle },
  postprocessing_failed: { label: 'Scoring failed', variant: 'error', icon: AlertTriangle },
  result_persistence_failed: { label: 'Failed to save result', variant: 'error', icon: AlertTriangle },
}

export const TERMINAL_SCAN_STATUSES = new Set<ScanRecordStatus>([
  'completed',
  'failed',
  'validation_failed',
  'upload_failed',
  'cancelled',
  'expired',
  'model_load_failed',
  'ai_preprocessing_failed',
  'feature_extraction_failed',
  'inference_failed',
  'postprocessing_failed',
  'result_persistence_failed',
])

export function ScanStatusBadge({ status }: { status: ScanRecordStatus }) {
  const cfg = STATUS_CONFIG[status]
  const Icon = cfg.icon
  return (
    <Badge variant={cfg.variant} className="gap-1.5 whitespace-nowrap">
      <Icon className={cn('w-3 h-3', cfg.spin && 'animate-spin')} aria-hidden="true" />
      {cfg.label}
    </Badge>
  )
}
