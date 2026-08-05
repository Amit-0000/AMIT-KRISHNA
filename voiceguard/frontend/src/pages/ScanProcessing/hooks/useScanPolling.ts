import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { pollScanStatus, startAIProcessing, type PollPhase } from '../services/processingApi'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PollingState {
  phase: PollPhase | 'initializing'
  progressPct: number
  currentStep: string
  errorMessage: string | null
  elapsedMs: number
}

const INITIAL: PollingState = {
  phase: 'initializing',
  progressPct: 0,
  currentStep: 'Starting analysis…',
  errorMessage: null,
  elapsedMs: 0,
}

// 1.2 s between polls — fast enough to feel live, slow enough not to hammer the API
const POLL_MS = 1200
// Backoff on network error
const BACKOFF_MS = 2400
// Brief pause at 100 % so the user sees "complete" before redirect
const COMPLETION_PAUSE_MS = 750

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useScanPolling(scanId: string): PollingState {
  const navigate = useNavigate()
  const [state, setState] = useState<PollingState>(INITIAL)
  // Guards startAIProcessing to fire at most once per mount — the backend
  // is idempotent-safe against a duplicate call regardless (see
  // processingApi.startAIProcessing), this just avoids firing it on every
  // 1.2s poll while the scan is still mid-pipeline.
  const aiProcessingStarted = useRef(false)

  // ── Elapsed timer ────────────────────────────────────────────────────────────
  useEffect(() => {
    const startedAt = Date.now()
    const id = setInterval(() => {
      setState((prev) => ({ ...prev, elapsedMs: Date.now() - startedAt }))
    }, 500)
    return () => clearInterval(id)
  }, [])

  // ── Polling loop ─────────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false
    let nextPoll: ReturnType<typeof setTimeout> | null = null

    const poll = async () => {
      if (cancelled) return

      try {
        const update = await pollScanStatus(scanId)

        if (update.status === 'ready_for_ai' && !aiProcessingStarted.current) {
          aiProcessingStarted.current = true
          await startAIProcessing(scanId)
        }

        if (cancelled) return

        setState((prev) => ({
          ...prev,
          phase: update.phase,
          progressPct: update.progressPct,
          currentStep: update.currentStep,
          errorMessage: update.errorMessage ?? null,
        }))

        if (update.phase === 'completed') {
          nextPoll = setTimeout(() => {
            if (!cancelled) navigate(`/scan/${scanId}`, { replace: true })
          }, COMPLETION_PAUSE_MS)
          return
        }

        if (update.phase === 'failed') return  // halt polling — error UI shown

        nextPoll = setTimeout(poll, POLL_MS)
      } catch {
        if (!cancelled) nextPoll = setTimeout(poll, BACKOFF_MS)
      }
    }

    poll()

    return () => {
      cancelled = true
      if (nextPoll !== null) clearTimeout(nextPoll)
    }
  }, [scanId, navigate])

  return state
}
