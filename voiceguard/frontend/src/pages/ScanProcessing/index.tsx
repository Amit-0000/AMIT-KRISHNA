import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { X } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { useScanPolling } from './hooks/useScanPolling'
import { resetMockCount } from './services/processingApi'
import { ProcessingAnimation } from './components/ProcessingAnimation'
import { ProcessingSteps } from './components/ProcessingSteps'
import { ProcessingProgress } from './components/ProcessingProgress'
import { ProcessingErrorState } from './components/ProcessingErrorState'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtElapsed(ms: number): string {
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  return `${m}m ${s % 60}s`
}

// ─── Inner content — keyed for retry remount ─────────────────────────────────

interface ContentProps {
  scanId: string
  onRetry: () => void
}

function ScanProcessingContent({ scanId, onRetry }: ContentProps) {
  const state = useScanPolling(scanId)

  const isActive    = state.phase === 'initializing' || state.phase === 'pending' || state.phase === 'processing'
  const isCompleted = state.phase === 'completed'
  const isFailed    = state.phase === 'failed'

  const displayProgress = isCompleted ? 100 : state.progressPct

  if (isFailed) {
    return (
      <ProcessingErrorState
        message={state.errorMessage ?? 'Audio analysis failed. Please try again.'}
        onRetry={onRetry}
      />
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0, 0, 1] }}
      className="space-y-5"
    >
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex flex-col items-center text-center pt-2 pb-1">
        <ProcessingAnimation isActive={isActive} />

        <h1 className="mt-4 text-display-sm font-bold text-text-primary">
          {isCompleted ? 'Analysis complete' : 'Analyzing your audio'}
        </h1>
        <p className="mt-1.5 text-sm text-text-secondary">
          {isCompleted
            ? 'Redirecting you to the result…'
            : 'Forensic-grade AI detection in progress'}
        </p>

        {/* Screen reader live region for step transitions */}
        <p
          className="sr-only"
          role="status"
          aria-live="polite"
          aria-atomic="true"
        >
          {state.currentStep}
        </p>
      </div>

      {/* ── Progress + steps card ────────────────────────────────────── */}
      <div className="card-base rounded-xl p-5 space-y-5">
        <ProcessingProgress progressPct={displayProgress} />

        <div className="h-px bg-chrome/5" role="separator" />

        <ProcessingSteps
          progressPct={displayProgress}
          isCompleted={isCompleted}
        />
      </div>

      {/* ── Elapsed + cancel ─────────────────────────────────────────── */}
      {!isCompleted && (
        <div className="flex items-center justify-between px-1 text-xs text-text-tertiary">
          <span>
            Elapsed:{' '}
            <span
              className="font-mono tabular-nums"
              aria-label={`Elapsed time: ${fmtElapsed(state.elapsedMs)}`}
            >
              {fmtElapsed(state.elapsedMs)}
            </span>
          </span>
          <Link
            to="/scan/new"
            className="flex items-center gap-1 hover:text-text-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
            aria-label="Cancel analysis and return to upload"
          >
            <X className="w-3 h-3" aria-hidden="true" />
            Cancel
          </Link>
        </div>
      )}
    </motion.div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function ScanProcessingPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const scanId = searchParams.get('id')

  // Retry key — incrementing causes ScanProcessingContent to fully remount,
  // restarting the polling loop from scratch without a full page reload.
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    if (!scanId) navigate('/scan/new', { replace: true })
  }, [scanId, navigate])

  if (!scanId) return null

  const handleRetry = () => {
    resetMockCount()
    setRetryKey((k) => k + 1)
  }

  return (
    <PageContainer maxWidth="sm">
      <ScanProcessingContent
        key={retryKey}
        scanId={scanId}
        onRetry={handleRetry}
      />
    </PageContainer>
  )
}
