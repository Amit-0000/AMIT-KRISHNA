import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  ExternalLink,
  Trash2,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  FileAudio,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tooltip, TooltipProvider } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { formatRelativeTime, formatDuration } from '@/lib/utils'
import type { ScanResult, Verdict } from '@/types'
import type { SortField, SortDir } from '../types'
import { useRecentScans } from '../hooks/useRecentScans'

// ─── Verdict helpers ──────────────────────────────────────────────────────────

const VERDICT_CONFIG: Record<
  Verdict,
  { label: string; icon: typeof CheckCircle2; badgeVariant: 'human' | 'ai' | 'uncertain' }
> = {
  human:        { label: 'Human',     icon: CheckCircle2, badgeVariant: 'human' },
  ai_generated: { label: 'AI Generated', icon: AlertTriangle, badgeVariant: 'ai' },
  uncertain:    { label: 'Uncertain', icon: HelpCircle, badgeVariant: 'uncertain' },
}

function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const cfg = VERDICT_CONFIG[verdict]
  const Icon = cfg.icon
  return (
    <Badge variant={cfg.badgeVariant} className="gap-1.5 whitespace-nowrap">
      <Icon className="w-3 h-3" aria-hidden="true" />
      {cfg.label}
    </Badge>
  )
}

// ─── Confidence mini-bar ──────────────────────────────────────────────────────

function ConfidenceBar({ value, verdict }: { value: number; verdict: Verdict }) {
  const color =
    verdict === 'human'
      ? 'bg-human'
      : verdict === 'ai_generated'
      ? 'bg-ai'
      : 'bg-uncertain'

  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="flex-1 h-1.5 rounded-full bg-chrome/8 overflow-hidden">
        <div
          className={cn('h-full rounded-full', color)}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-xs tabular-nums font-medium text-text-primary w-10 text-right">
        {value.toFixed(1)}%
      </span>
    </div>
  )
}

// ─── Sort icon ────────────────────────────────────────────────────────────────

function SortIcon({
  active,
  dir,
}: {
  active: boolean
  dir: SortDir
}) {
  if (!active) return <ChevronsUpDown className="w-3.5 h-3.5 opacity-30" aria-hidden="true" />
  return dir === 'asc' ? (
    <ChevronUp className="w-3.5 h-3.5 text-brand" aria-hidden="true" />
  ) : (
    <ChevronDown className="w-3.5 h-3.5 text-brand" aria-hidden="true" />
  )
}

// ─── Empty filtered ───────────────────────────────────────────────────────────

function EmptyFiltered({ query }: { query: string }) {
  return (
    <tr>
      <td colSpan={6} className="py-16 text-center">
        <Search className="w-8 h-8 text-text-tertiary mx-auto mb-3" aria-hidden="true" />
        <p className="text-sm font-medium text-text-secondary mb-1">
          No results for "{query}"
        </p>
        <p className="text-xs text-text-tertiary">Try a different filename or verdict filter.</p>
      </td>
    </tr>
  )
}

// ─── Row ─────────────────────────────────────────────────────────────────────

function ScanRow({
  scan,
  onDelete,
  deleting,
}: {
  scan: ScanResult
  onDelete: (id: string) => void
  deleting: boolean
}) {
  const navigate = useNavigate()

  return (
    <motion.tr
      layout
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18 }}
      className="group border-b border-chrome/4 hover:bg-chrome/[0.02] transition-colors cursor-pointer"
      onClick={() => navigate(`/history/${scan.scan_id}`)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') navigate(`/history/${scan.scan_id}`)
      }}
      tabIndex={0}
      role="row"
      aria-label={`${scan.file_name} — ${scan.verdict}`}
    >
      {/* File name */}
      <td className="py-3 pl-4 pr-3 max-w-[200px]">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="flex-shrink-0 w-7 h-7 rounded-md bg-chrome/5 border border-chrome/8 flex items-center justify-center">
            <FileAudio className="w-3.5 h-3.5 text-text-tertiary" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-text-primary truncate" title={scan.file_name}>
              {scan.file_name}
            </p>
            <p className="text-xs text-text-tertiary">
              {formatDuration(scan.file_duration_seconds)}
            </p>
          </div>
        </div>
      </td>

      {/* Verdict */}
      <td className="py-3 px-3">
        <VerdictBadge verdict={scan.verdict} />
      </td>

      {/* Confidence */}
      <td className="py-3 px-3 hidden sm:table-cell">
        <ConfidenceBar value={scan.confidence} verdict={scan.verdict} />
      </td>

      {/* Processing time */}
      <td className="py-3 px-3 hidden lg:table-cell">
        <span className="text-xs tabular-nums text-text-secondary">
          {scan.inference_time_ms}ms
        </span>
      </td>

      {/* Date */}
      <td className="py-3 px-3 hidden md:table-cell">
        <span className="text-xs text-text-tertiary whitespace-nowrap">
          {formatRelativeTime(scan.created_at)}
        </span>
      </td>

      {/* Actions */}
      <td
        className="py-3 pl-3 pr-4"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
          <TooltipProvider>
            <Tooltip content="View result" side="top">
              <button
                onClick={() => navigate(`/history/${scan.scan_id}`)}
                className="flex items-center justify-center w-7 h-7 rounded-md text-text-tertiary hover:text-text-primary hover:bg-chrome/8 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                aria-label={`View ${scan.file_name}`}
              >
                <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
              </button>
            </Tooltip>
            <Tooltip content="Delete" side="top">
              <button
                onClick={() => onDelete(scan.scan_id)}
                disabled={deleting}
                className="flex items-center justify-center w-7 h-7 rounded-md text-text-tertiary hover:text-ai hover:bg-ai-muted transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ai disabled:opacity-40"
                aria-label={`Delete ${scan.file_name}`}
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

// ─── Main table ───────────────────────────────────────────────────────────────

export function RecentAnalysisTable() {
  const {
    scans,
    filteredCount,
    isLoading,
    isError,
    refetch,
    search,
    setSearch,
    sortBy,
    sortDir,
    sortToggle,
    page,
    setPage,
    totalPages,
    pageSize,
    deleteOne,
    isDeleting,
  } = useRecentScans()

  const SORTABLE_COLS: Array<{ key: SortField; label: string; hideClass?: string }> = [
    { key: 'file_name',        label: 'File' },
    { key: 'verdict',          label: 'Verdict' },
    { key: 'confidence',       label: 'Confidence', hideClass: 'hidden sm:table-cell' },
    { key: 'inference_time_ms',label: 'Time',       hideClass: 'hidden lg:table-cell' },
    { key: 'created_at',       label: 'Date',       hideClass: 'hidden md:table-cell' },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.14, ease: [0.25, 0, 0, 1] }}
      className="card-base rounded-xl overflow-hidden"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 px-5 py-4 border-b border-chrome/6">
        <div className="flex-1">
          <h2 className="text-heading-md font-semibold text-text-primary">Recent Analyses</h2>
          {!isLoading && (
            <p className="text-xs text-text-tertiary mt-0.5">
              {filteredCount > 0 ? `${filteredCount} result${filteredCount !== 1 ? 's' : ''}` : 'No results'}
              {search && ` for "${search}"`}
            </p>
          )}
        </div>
        <div className="w-full sm:w-64">
          <Input
            leftIcon={<Search className="w-3.5 h-3.5" />}
            placeholder="Search by filename or verdict…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search analyses"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm" role="grid" aria-label="Recent analyses">
          <thead>
            <tr className="border-b border-chrome/6" role="row">
              {SORTABLE_COLS.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  className={cn(
                    'py-3 text-left font-medium text-text-tertiary text-xs uppercase tracking-wider',
                    col.key === 'file_name' ? 'pl-4 pr-3' : 'px-3',
                    col.hideClass
                  )}
                  aria-sort={
                    sortBy === col.key
                      ? sortDir === 'asc'
                        ? 'ascending'
                        : 'descending'
                      : 'none'
                  }
                >
                  <button
                    onClick={() => sortToggle(col.key)}
                    className="inline-flex items-center gap-1.5 hover:text-text-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
                  >
                    {col.label}
                    <SortIcon active={sortBy === col.key} dir={sortDir} />
                  </button>
                </th>
              ))}
              <th scope="col" className="py-3 pl-3 pr-4">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody role="rowgroup">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-chrome/4" role="row">
                  {Array.from({ length: 6 }).map((__, j) => (
                    <td key={j} className="py-3 px-3">
                      <Skeleton className="h-4 rounded" style={{ width: j === 0 ? '80%' : j === 5 ? '40px' : '60%' }} />
                    </td>
                  ))}
                </tr>
              ))
            ) : isError ? (
              <tr role="row">
                <td colSpan={6} className="py-12 text-center">
                  <p className="text-sm text-text-secondary mb-3">Failed to load analyses</p>
                  <Button variant="outline" size="sm" onClick={() => refetch()}>
                    Try again
                  </Button>
                </td>
              </tr>
            ) : scans.length === 0 && search ? (
              <EmptyFiltered query={search} />
            ) : (
              <AnimatePresence mode="popLayout">
                {scans.map((scan) => (
                  <ScanRow
                    key={scan.scan_id}
                    scan={scan}
                    onDelete={deleteOne}
                    deleting={isDeleting}
                  />
                ))}
              </AnimatePresence>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {!isLoading && filteredCount > pageSize && (
        <div
          className="flex items-center justify-between gap-4 px-5 py-3 border-t border-chrome/6"
          role="navigation"
          aria-label="Table pagination"
        >
          <p className="text-xs text-text-tertiary">
            Showing {(page - 1) * pageSize + 1}–
            {Math.min(page * pageSize, filteredCount)} of {filteredCount}
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
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
              .reduce<Array<number | 'ellipsis'>>((acc, p, idx, arr) => {
                if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push('ellipsis')
                acc.push(p)
                return acc
              }, [])
              .map((item, idx) =>
                item === 'ellipsis' ? (
                  <span key={`e${idx}`} className="w-7 text-center text-xs text-text-tertiary">
                    …
                  </span>
                ) : (
                  <button
                    key={item}
                    onClick={() => setPage(item)}
                    className={cn(
                      'w-7 h-7 rounded-md text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                      page === item
                        ? 'bg-brand text-white'
                        : 'text-text-tertiary hover:text-text-primary hover:bg-chrome/5'
                    )}
                    aria-label={`Page ${item}`}
                    aria-current={page === item ? 'page' : undefined}
                  >
                    {item}
                  </button>
                )
              )}
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
