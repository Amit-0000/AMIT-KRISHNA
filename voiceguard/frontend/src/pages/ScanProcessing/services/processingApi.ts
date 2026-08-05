import { scanApi } from '@/services/api'
import type { ScanRecordStatus } from '@/types'

// ─── Contract ─────────────────────────────────────────────────────────────────
// useScanPolling and ScanProcessingPage depend on exactly this shape.

export type PollPhase = 'pending' | 'processing' | 'completed' | 'failed'

export interface PollUpdate {
  phase: PollPhase
  progressPct: number
  currentStep: string
  errorMessage?: string
  status: ScanRecordStatus
}

// This slice's upload lifecycle (Slice 02) hands off at READY_FOR_AI to the
// AI Processing Pipeline (Slice 03), which runs all the way to COMPLETED —
// a scan_results row now exists once that happens, so 'completed' is the
// only status this page treats as truly done (was previously READY_FOR_AI,
// before this slice existed).
const STEP_LABELS: Partial<Record<ScanRecordStatus, string>> = {
  created: 'Preparing upload…',
  validating: 'Validating file…',
  uploading: 'Uploading…',
  queued: 'Queued for analysis',
  preprocessing: 'Preprocessing audio…',
  ready_for_ai: 'Starting AI analysis…',
  preparing_model: 'Preparing detection model…',
  loading_model: 'Loading detection model…',
  ai_preprocessing: 'Analyzing audio signal…',
  feature_extraction: 'Extracting audio features…',
  running_inference: 'Running deepfake detection…',
  postprocessing: 'Scoring confidence…',
  generating_explanation: 'Generating explanation…',
  saving_results: 'Saving results…',
}

const PROGRESS_BY_STATUS: Partial<Record<ScanRecordStatus, number>> = {
  created: 3,
  validating: 8,
  uploading: 15,
  queued: 22,
  preprocessing: 30,
  ready_for_ai: 35,
  preparing_model: 40,
  loading_model: 48,
  ai_preprocessing: 58,
  feature_extraction: 68,
  running_inference: 80,
  postprocessing: 90,
  generating_explanation: 95,
  saving_results: 98,
}

const FAILURE_STATUSES = new Set<ScanRecordStatus>([
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

/**
 * Fires POST /scans/{id}/process the moment a scan reaches READY_FOR_AI —
 * the AI Processing Pipeline's actual entry point (api.inference.service.
 * start_processing requires exactly that status). The backend itself is
 * idempotent-guarded (a second call 422s with SCAN_NOT_READY_FOR_PROCESSING
 * once the scan has moved on), so an accidental duplicate call from a race
 * between two polls is harmless — but useScanPolling still guards this with
 * a ref so it's only attempted once per mount in the common case.
 */
export async function startAIProcessing(scanId: string): Promise<void> {
  try {
    await scanApi.process(scanId)
  } catch {
    // Already started (or moved on) by the time this fired — the next poll
    // will reflect whatever the real current status is either way.
  }
}

export async function pollScanStatus(scanId: string): Promise<PollUpdate> {
  // Network/5xx errors intentionally propagate to the caller — useScanPolling
  // already retries transient failures with backoff; simulating a fake
  // "completed" result here would hide real outages instead.
  const { data } = await scanApi.pollStatus(scanId)
  const status = data.scan.status

  if (status === 'completed') {
    return { phase: 'completed', progressPct: 100, currentStep: 'Analysis complete', status }
  }
  if (FAILURE_STATUSES.has(status)) {
    return {
      phase: 'failed',
      progressPct: 0,
      currentStep: 'Failed',
      errorMessage: data.scan.error_message ?? 'Audio analysis failed. Please try again.',
      status,
    }
  }
  return {
    phase: 'processing',
    progressPct: PROGRESS_BY_STATUS[status] ?? 10,
    currentStep: STEP_LABELS[status] ?? 'Processing…',
    status,
  }
}

export function resetMockCount(): void {
  // No-op: retained so ScanProcessingPage's retry handler doesn't need to
  // change. There's no mock simulation left to reset now that this polls
  // the real backend.
}
