import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ChevronDown, History, RotateCcw } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { cn, formatDate } from '@/lib/utils'
import { scanApi } from '@/services/api'
import { VerdictCard } from './components/VerdictCard'
import { TechnicalDetails } from './components/TechnicalDetails'
import { ExplanationPanel } from './components/ExplanationPanel'
import { useScanExplanation, useScanResult, useScanTechnical } from './hooks/useScanResult'

// ─── Not-yet-complete fallback ────────────────────────────────────────────────
// Direct navigation (bookmark, refresh, back button) can land here before a
// scan has actually reached COMPLETED — GET /result 404s with RESULT_NOT_FOUND
// in that case. Route the user somewhere useful instead of a bare error.

function NotReadyFallback({ scanId }: { scanId: string }) {
  const navigate = useNavigate()
  const [checking, setChecking] = useState(true)
  const [failure, setFailure] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    scanApi
      .status(scanId)
      .then(({ data }) => {
        if (cancelled) return
        const status = data.scan.status
        const stillProcessing = !['completed'].includes(status) && !status.endsWith('_failed') && status !== 'failed'
        if (stillProcessing) {
          navigate(`/scan/processing?id=${scanId}`, { replace: true })
        } else if (status === 'completed') {
          // Result briefly not yet queryable right after SAVING_RESULTS commits — retry once.
          navigate(0)
        } else {
          setFailure(data.scan.error_message ?? 'Analysis did not complete successfully.')
          setChecking(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setFailure('This scan could not be found.')
          setChecking(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [scanId, navigate])

  if (checking) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <Skeleton className="h-8 w-48 rounded" />
      </div>
    )
  }

  return (
    <div className="card-base rounded-xl p-8 text-center space-y-4">
      <p className="text-text-secondary">{failure}</p>
      <Link to="/scan/new">
        <Button className="gap-2">
          <RotateCcw className="w-4 h-4" aria-hidden="true" />
          Start a new scan
        </Button>
      </Link>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function ScanResultPage() {
  const { scanId } = useParams<{ scanId: string }>()
  const [showTechnical, setShowTechnical] = useState(false)

  const { result, isLoading, isError } = useScanResult(scanId ?? '')
  const { technical, isLoading: technicalLoading } = useScanTechnical(scanId ?? '', showTechnical)
  const { explanation, isLoading: explanationLoading } = useScanExplanation(scanId ?? '', !!result)

  if (!scanId) return null

  if (isLoading) {
    return (
      <PageContainer maxWidth="sm">
        <div className="space-y-4">
          <Skeleton className="h-56 rounded-2xl" />
          <Skeleton className="h-40 rounded-xl" />
        </div>
      </PageContainer>
    )
  }

  if (isError || !result) {
    return (
      <PageContainer maxWidth="sm">
        <NotReadyFallback scanId={scanId} />
      </PageContainer>
    )
  }

  return (
    <PageContainer maxWidth="sm">
      <div className="space-y-5">
        <VerdictCard verdict={result.verdict} confidence={result.confidence} />

        <ExplanationPanel explanation={explanation} isLoading={explanationLoading} />

        <div className="card-base rounded-xl overflow-hidden">
          <button
            onClick={() => setShowTechnical((v) => !v)}
            className="w-full flex items-center justify-between p-4 text-sm font-medium text-text-primary hover:bg-white/[0.02] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            aria-expanded={showTechnical}
          >
            Technical details
            <ChevronDown
              className={cn('w-4 h-4 transition-transform', showTechnical && 'rotate-180')}
              aria-hidden="true"
            />
          </button>
          {showTechnical && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="border-t border-white/6">
              <TechnicalDetails technical={technical} isLoading={technicalLoading} />
            </motion.div>
          )}
        </div>

        <p className="text-center text-xs text-text-tertiary">
          Analyzed {formatDate(result.created_at)} · {result.processing_time_ms} ms total
        </p>

        <div className="flex items-center justify-center gap-3 pt-1">
          <Link to="/history">
            <Button variant="outline" className="gap-2">
              <History className="w-4 h-4" aria-hidden="true" />
              View history
            </Button>
          </Link>
          <Link to="/scan/new">
            <Button className="gap-2">
              <RotateCcw className="w-4 h-4" aria-hidden="true" />
              Scan another file
            </Button>
          </Link>
        </div>
      </div>
    </PageContainer>
  )
}
