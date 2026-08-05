import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { ChevronDown, ChevronLeft, FileAudio, RotateCcw, Trash2 } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { scanApi } from '@/services/api'
import { parseApiError } from '@/lib/apiError'
import { cn, formatDate, formatDuration, formatFileSize, formatRelativeTime } from '@/lib/utils'
import { ScanStatusBadge, TERMINAL_SCAN_STATUSES } from '@/pages/History/components/ScanStatusBadge'
import { VerdictCard } from '@/pages/ScanResult/components/VerdictCard'
import { ExplanationPanel } from '@/pages/ScanResult/components/ExplanationPanel'
import { TechnicalDetails } from '@/pages/ScanResult/components/TechnicalDetails'
import { useScanExplanation, useScanResult, useScanTechnical } from '@/pages/ScanResult/hooks/useScanResult'
import { toast } from 'sonner'

function DetailSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-20 rounded-xl" />
      <Skeleton className="h-56 rounded-2xl" />
      <Skeleton className="h-40 rounded-xl" />
    </div>
  )
}

function NotFoundState() {
  return (
    <div className="card-base rounded-xl p-10 text-center">
      <p className="text-sm text-text-secondary mb-4">This scan could not be found.</p>
      <Link to="/history">
        <Button variant="secondary" className="gap-2">
          <ChevronLeft className="w-4 h-4" aria-hidden="true" />
          Back to history
        </Button>
      </Link>
    </div>
  )
}

export function ScanDetailPage() {
  const { scanId } = useParams<{ scanId: string }>()
  const navigate = useNavigate()
  const [showTechnical, setShowTechnical] = useState(false)

  const scanQuery = useQuery({
    queryKey: ['scan-status', scanId],
    queryFn: async () => {
      const { data } = await scanApi.status(scanId!)
      return data.scan
    },
    enabled: !!scanId,
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (!status) return false
      return TERMINAL_SCAN_STATUSES.has(status) ? false : 5000
    },
  })

  const isCompleted = scanQuery.data?.status === 'completed'

  const { result, isLoading: resultLoading, isError: resultError } = useScanResult(isCompleted ? scanId ?? '' : '')
  const { technical, isLoading: technicalLoading } = useScanTechnical(scanId ?? '', showTechnical && isCompleted)
  const { explanation, isLoading: explanationLoading } = useScanExplanation(scanId ?? '', isCompleted && !!result)

  async function handleDelete() {
    if (!scanId) return
    try {
      await scanApi.delete(scanId)
      toast.success('Scan deleted')
      navigate('/history')
    } catch (err) {
      toast.error(parseApiError(err).message)
    }
  }

  if (!scanId) return null

  if (scanQuery.isLoading) {
    return (
      <PageContainer maxWidth="sm" title="Scan detail">
        <DetailSkeleton />
      </PageContainer>
    )
  }

  if (scanQuery.isError || !scanQuery.data) {
    return (
      <PageContainer maxWidth="sm" title="Scan detail">
        <NotFoundState />
      </PageContainer>
    )
  }

  const scan = scanQuery.data

  return (
    <PageContainer maxWidth="sm">
      <div className="space-y-5">
        <Link
          to="/history"
          className="inline-flex items-center gap-1.5 text-sm text-text-tertiary hover:text-text-secondary transition-colors"
        >
          <ChevronLeft className="w-4 h-4" aria-hidden="true" />
          Back to history
        </Link>

        {/* File info header */}
        <div className="card-base rounded-xl p-4 flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-white/5 border border-white/8 flex items-center justify-center flex-shrink-0">
            <FileAudio className="w-5 h-5 text-text-tertiary" aria-hidden="true" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-text-primary truncate" title={scan.original_filename}>
              {scan.original_filename}
            </p>
            <p className="text-xs text-text-tertiary mt-0.5">
              {formatFileSize(scan.file_size_bytes)}
              {scan.duration_seconds != null && ` · ${formatDuration(scan.duration_seconds)}`}
              {' · '}Uploaded {formatRelativeTime(scan.created_at)}
            </p>
          </div>
          <ScanStatusBadge status={scan.status} />
        </div>

        {isCompleted ? (
          resultLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-56 rounded-2xl" />
              <Skeleton className="h-40 rounded-xl" />
            </div>
          ) : resultError || !result ? (
            <div className="card-base rounded-xl p-8 text-center">
              <p className="text-sm text-text-secondary">
                This scan finished, but its result could not be loaded.
              </p>
            </div>
          ) : (
            <>
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
            </>
          )
        ) : (
          <div className="card-base rounded-xl p-8 text-center space-y-4">
            {TERMINAL_SCAN_STATUSES.has(scan.status) ? (
              <>
                <p className="text-sm text-text-secondary">
                  {scan.error_message ?? 'This scan did not complete successfully.'}
                </p>
                <div className="flex items-center justify-center gap-3">
                  <Link to="/scan/new">
                    <Button className="gap-2">
                      <RotateCcw className="w-4 h-4" aria-hidden="true" />
                      Start a new scan
                    </Button>
                  </Link>
                  <Button variant="secondary" className="gap-2" onClick={handleDelete}>
                    <Trash2 className="w-4 h-4" aria-hidden="true" />
                    Delete
                  </Button>
                </div>
              </>
            ) : (
              <>
                <p className="text-sm text-text-secondary">This scan is still in progress.</p>
                <Button
                  className="gap-2"
                  onClick={() => navigate(`/scan/processing?id=${scanId}`)}
                >
                  Watch live progress
                </Button>
              </>
            )}
          </div>
        )}
      </div>
    </PageContainer>
  )
}
