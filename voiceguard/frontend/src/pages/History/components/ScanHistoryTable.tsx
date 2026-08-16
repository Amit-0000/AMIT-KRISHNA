import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'
import {
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  FileAudio,
  Trash2,
  Ban,
  ExternalLink,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tooltip, TooltipProvider } from '@/components/ui/tooltip'
import { Button } from '@/components/ui/button'
import { cn, formatRelativeTime, formatDuration, formatFileSize } from '@/lib/utils'
import { parseApiError } from '@/lib/apiError'
import type { ScanRecord, ScanRecordStatus } from '@/types'
import { useScanHistory } from '../hooks/useScanHistory'
import { ScanStatusBadge, TERMINAL_SCAN_STATUSES } from './ScanStatusBadge'
import { EmptyHistory } from './EmptyHistory'

const STATUS_FILTER_OPTIONS: Array<{ value: ScanRecordStatus | 'all'; label: string }> = [
  { value: 'all', label: 'All statuses' },
  { value: 'queued', label: 'Queued' },
  { value: 'preprocessing', label: 'Processing' },
  { value: 'ready_for_ai', label: 'Ready for AI' },
  { value: 'running_inference', label: 'Analyzing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'validation_failed', label: 'Rejected' },
  { value: 'upload_failed', label: 'Upload failed' },
  { value: 'inference_failed', label: 'Detection failed' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'expired', label: 'Expired' },
]

function ScanRow({
  scan,
  onCancel,
  onDelete,
  isCancelling,
  isDeleting,
}: {
  scan: ScanRecord
  onCancel: (id: string) => void
  onDelete: (id: string) => void
  isCancelling: boolean
  isDeleting: boolean
}) {
  const navigate = useNavigate()
  const isTerminal = TERMINAL_SCAN_STATUSES.has(scan.status)
  const busy = isCancelling || isDeleting

  return (
    <motion.tr
      layout
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18 }}
      className="group border-b border-chrome/4 hover:bg-chrome/[0.02] transition-colors cursor-pointer"
      onClick={() => navigate(`/history/${scan.id}`)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') navigate(`/history/${scan.id}`)
      }}
      tabIndex={0}
      role="row"
      aria-label={`${scan.original_filename} — ${scan.status}`}
    >
      <td className="py-3 pl-4 pr-3 max-w-[220px]">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="flex-shrink-0 w-7 h-7 rounded-md bg-chrome/5 border border-chrome/8 flex items-center justify-center">
            <FileAudio className="w-3.5 h-3.5 text-text-tertiary" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-text-primary truncate" title={scan.original_filename}>
              {scan.original_filename}
            </p>
            <p className="text-xs text-text-tertiary">
              {formatFileSize(scan.file_size_bytes)}
              {scan.duration_seconds != null && ` · ${formatDuration(scan.duration_seconds)}`}
            </p>
          </div>
        </div>
      </td>

      <td className="py-3 px-3">
        <div className="flex items-center gap-1.5 flex-wrap">
          <ScanStatusBadge status={scan.status} />
          {scan.malware_scan_status === 'not_scanned' && (
            <Badge variant="warning" className="whitespace-nowrap" title="Processed without malware scanning">
              Unscanned
            </Badge>
          )}
        </div>
        {scan.error_message && (
          <p className="mt-1 text-xs text-text-tertiary max-w-[220px] truncate" title={scan.error_message}>
            {scan.error_message}
          </p>
        )}
      </td>

      <td className="py-3 px-3 hidden md:table-cell">
        <span className="text-xs text-text-tertiary whitespace-nowrap">
          {formatRelativeTime(scan.created_at)}
        </span>
      </td>

      <td
        className="py-3 pl-3 pr-4"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
          <TooltipProvider>
            <Tooltip content="View details" side="top">
              <button
                onClick={() => navigate(`/history/${scan.id}`)}
                className="flex items-center justify-center w-7 h-7 rounded-md text-text-tertiary hover:text-text-primary hover:bg-chrome/8 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                aria-label={`View ${scan.original_filename}`}
              >
                <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
              </button>
            </Tooltip>
            {!isTerminal && (
              <Tooltip content="Cancel scan" side="top">
                <button
                  onClick={() => onCancel(scan.id)}
                  disabled={busy}
                  className="flex items-center justify-center w-7 h-7 rounded-md text-text-tertiary hover:text-uncertain hover:bg-uncertain-muted transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-uncertain disabled:opacity-40"
                  aria-label={`Cancel ${scan.original_filename}`}
                >
                  <Ban className="w-3.5 h-3.5" aria-hidden="true" />
                </button>
              </Tooltip>
            )}
            <Tooltip content="Delete" side="top">
              <button
                onClick={() => onDelete(scan.id)}
                disabled={busy}
                className="flex items-center justify-center w-7 h-7 rounded-md text-text-tertiary hover:text-ai hover:bg-ai-muted transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ai disabled:opacity-40"
                aria-label={`Delete ${scan.original_filename}`}
              >
                <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
              </button>
            </Tooltip>
          </TooltipProvider>
        </div>
      </td>
    </motion.tr>
  )
}

export function ScanHistoryTable() {
  const {
    scans,
    total,
    totalPages,
    isLoading,
    isError,
    refetch,
    page,
    setPage,
    pageSize,
    statusFilter,
    setStatusFilter,
    sort,
    toggleSort,
    cancelScan,
    cancellingId,
    isCancelling,
    deleteScan,
    deletingId,
    isDeleting,
  } = useScanHistory()

  function handleCancel(id: string) {
    cancelScan(id, {
      onError: (err) => toast.error(parseApiError(err).message),
    })
  }

  function handleDelete(id: string) {
    deleteScan(id, {
      onError: (err) => toast.error(parseApiError(err).message),
    })
  }

  if (!isLoading && !isError && total === 0 && statusFilter === 'all') {
    return <EmptyHistory />
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0, 0, 1] }}
      className="card-base rounded-xl overflow-hidden"
    >
      {/* Header / filters */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 px-5 py-4 border-b border-chrome/6">
        <div className="flex-1">
          <h2 className="text-heading-md font-semibold text-text-primary">Your scans</h2>
          {!isLoading && (
            <p className="text-xs text-text-tertiary mt-0.5">
              {total} scan{total !== 1 ? 's' : ''}
            </p>
          )}
        </div>
        <label className="sr-only" htmlFor="scan-status-filter">
          Filter by status
        </label>
        <select
          id="scan-status-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as ScanRecordStatus | 'all')}
          className="w-full sm:w-44 rounded-lg border border-chrome/10 bg-chrome/5 px-3 py-2 text-sm text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
        >
          {STATUS_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm" role="grid" aria-label="Scan history">
          <thead>
            <tr className="border-b border-chrome/6" role="row">
              <th scope="col" className="py-3 pl-4 pr-3 text-left font-medium text-text-tertiary text-xs uppercase tracking-wider">
                File
              </th>
              <th scope="col" className="py-3 px-3 text-left font-medium text-text-tertiary text-xs uppercase tracking-wider">
                Status
              </th>
              <th
                scope="col"
                className="py-3 px-3 hidden md:table-cell text-left font-medium text-text-tertiary text-xs uppercase tracking-wider"
                aria-sort={sort === '-created_at' ? 'descending' : 'ascending'}
              >
                <button
                  onClick={toggleSort}
                  className="inline-flex items-center gap-1.5 hover:text-text-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
                >
                  Uploaded
                  {sort === '-created_at' ? (
                    <ChevronDown className="w-3.5 h-3.5 text-brand" aria-hidden="true" />
                  ) : (
                    <ChevronUp className="w-3.5 h-3.5 text-brand" aria-hidden="true" />
                  )}
                </button>
              </th>
              <th scope="col" className="py-3 pl-3 pr-4">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody role="rowgroup">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-chrome/4" role="row">
                  {Array.from({ length: 4 }).map((__, j) => (
                    <td key={j} className="py-3 px-3">
                      <Skeleton className="h-4 rounded" style={{ width: j === 0 ? '80%' : j === 3 ? '40px' : '60%' }} />
                    </td>
                  ))}
                </tr>
              ))
            ) : isError ? (
              <tr role="row">
                <td colSpan={4} className="py-12 text-center">
                  <p className="text-sm text-text-secondary mb-3">Failed to load scans</p>
                  <Button variant="outline" size="sm" onClick={() => refetch()}>
                    Try again
                  </Button>
                </td>
              </tr>
            ) : scans.length === 0 ? (
              <tr role="row">
                <td colSpan={4} className="py-16 text-center">
                  <p className="text-sm font-medium text-text-secondary mb-1">No scans match this filter</p>
                  <p className="text-xs text-text-tertiary">Try a different status.</p>
                </td>
              </tr>
            ) : (
              <AnimatePresence mode="popLayout">
                {scans.map((scan) => (
                  <ScanRow
                    key={scan.id}
                    scan={scan}
                    onCancel={handleCancel}
                    onDelete={handleDelete}
                    isCancelling={isCancelling && cancellingId === scan.id}
                    isDeleting={isDeleting && deletingId === scan.id}
                  />
                ))}
              </AnimatePresence>
            )}
          </tbody>
        </table>
      </div>

      {!isLoading && total > pageSize && (
        <div
          className="flex items-center justify-between gap-4 px-5 py-3 border-t border-chrome/6"
          role="navigation"
          aria-label="Table pagination"
        >
          <p className="text-xs text-text-tertiary">
            Page {page} of {totalPages}
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
              className="flex items-center justify-center w-7 h-7 rounded-md text-text-tertiary hover:text-text-primary hover:bg-chrome/5 disabled:opacity-30 disabled:cursor-not-allowed transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
              aria-label="Previous page"
            >
              <ChevronLeft className="w-4 h-4" aria-hidden="true" />
            </button>
            <span className={cn('text-xs text-text-tertiary px-2 tabular-nums')}>
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page === totalPages}
              className="flex items-center justify-center w-7 h-7 rounded-md text-text-tertiary hover:text-text-primary hover:bg-chrome/5 disabled:opacity-30 disabled:cursor-not-allowed transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
              aria-label="Next page"
            >
              <ChevronRight className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      )}
    </motion.div>
  )
}
