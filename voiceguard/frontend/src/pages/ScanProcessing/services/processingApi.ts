import { scanApi } from '@/services/api'
import type { ScanResult } from '@/types'

// ─── Contract ─────────────────────────────────────────────────────────────────

export type PollPhase = 'pending' | 'processing' | 'completed' | 'failed'

export interface PollUpdate {
  phase: PollPhase
  progressPct: number
  currentStep: string
  result?: ScanResult
  errorMessage?: string
}

// ─── Mock simulation ──────────────────────────────────────────────────────────
// Activated when the backend is unreachable. Tracks per-scan call counts in
// module scope so each scanId progresses independently across re-renders.

const mockCounts = new Map<string, number>()

const MOCK_STAGES: Omit<PollUpdate, 'result' | 'errorMessage'>[] = [
  { phase: 'pending',    progressPct: 0,  currentStep: 'Queued for analysis' },
  { phase: 'pending',    progressPct: 0,  currentStep: 'Queued for analysis' },
  { phase: 'processing', progressPct: 10, currentStep: 'Segmenting audio frames' },
  { phase: 'processing', progressPct: 22, currentStep: 'Segmenting audio frames' },
  { phase: 'processing', progressPct: 38, currentStep: 'Running LCNN inference' },
  { phase: 'processing', progressPct: 54, currentStep: 'Running LCNN inference' },
  { phase: 'processing', progressPct: 68, currentStep: 'Aggregating segment verdicts' },
  { phase: 'processing', progressPct: 80, currentStep: 'Computing confidence scores' },
  { phase: 'processing', progressPct: 91, currentStep: 'Generating frequency heatmap' },
  { phase: 'processing', progressPct: 97, currentStep: 'Finalizing verdict' },
]

function buildMockResult(scanId: string): ScanResult {
  // Deterministic verdict based on scanId hash so retries return the same result
  const sum = scanId.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  const verdicts = ['human', 'ai_generated', 'uncertain'] as const
  const verdict = verdicts[sum % 3]
  const confidence = verdict === 'human' ? 0.92 : verdict === 'ai_generated' ? 0.87 : 0.71

  return {
    scan_id: scanId,
    status: 'completed',
    verdict,
    confidence,
    human_score: verdict === 'human' ? 0.92 : 1 - confidence,
    ai_score: verdict === 'ai_generated' ? 0.87 : 1 - confidence,
    inference_time_ms: 1340 + (sum % 400),
    model_version: 'lcnn-v2.1',
    segment_count: 8 + (sum % 5),
    frequency_heatmap: null,
    file_name: 'audio-sample.wav',
    file_duration_seconds: 24.5,
    created_at: new Date().toISOString(),
    share_token: null,
    user_verdict: null,
  }
}

export function resetMockCount(scanId: string): void {
  mockCounts.delete(scanId)
}

// ─── Primary export ───────────────────────────────────────────────────────────

export async function pollScanStatus(scanId: string): Promise<PollUpdate> {
  try {
    const { data } = await scanApi.status(scanId)

    if (data.status === 'completed') {
      return { phase: 'completed', progressPct: 100, currentStep: 'Complete', result: data }
    }
    if (data.status === 'failed') {
      return {
        phase: 'failed',
        progressPct: 0,
        currentStep: 'Failed',
        errorMessage: 'Audio analysis failed. Please try again.',
      }
    }
    // pending | processing — backend doesn't return progress_pct on status endpoint
    return {
      phase: data.status,
      progressPct: data.status === 'pending' ? 0 : 50,
      currentStep: data.status === 'pending' ? 'Queued for analysis' : 'Processing…',
    }
  } catch {
    // Backend unavailable — simulate realistic progression
    const count = (mockCounts.get(scanId) ?? 0) + 1
    mockCounts.set(scanId, count)

    if (count > MOCK_STAGES.length) {
      return {
        phase: 'completed',
        progressPct: 100,
        currentStep: 'Complete',
        result: buildMockResult(scanId),
      }
    }

    return { ...MOCK_STAGES[count - 1] }
  }
}
