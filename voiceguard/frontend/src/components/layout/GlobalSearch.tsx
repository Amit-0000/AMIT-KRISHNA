import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  X,
  LayoutDashboard,
  Upload,
  Clock,
  HelpCircle,
  MessageSquare,
  Settings,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  HelpCircle as UncertainIcon,
  Keyboard,
} from 'lucide-react'
import { useUIStore } from '@/store/uiStore'
import { useKeyboard } from '@/hooks/useKeyboard'
import { cn } from '@/lib/utils'
import { fetchRecentScans } from '@/pages/Dashboard/services/dashboardApi'
import type { SearchResult } from '@/types'

// ─── Static quick-access results ─────────────────────────────────────────────

const QUICK_ACTIONS: SearchResult[] = [
  { id: 'new-scan', type: 'action', label: 'New Scan', description: 'Analyze an audio file', href: '/scan/new', icon: 'upload' },
  { id: 'dashboard', type: 'nav', label: 'Dashboard', description: 'Overview and recent activity', href: '/dashboard', icon: 'dashboard' },
  { id: 'history', type: 'nav', label: 'History', description: 'All past scan results', href: '/history', icon: 'clock' },
  { id: 'help', type: 'nav', label: 'Help Center', description: 'Guides and documentation', href: '/help', icon: 'help' },
  { id: 'feedback', type: 'nav', label: 'Give Feedback', description: 'Report issues or suggest improvements', href: '/feedback', icon: 'message' },
  { id: 'settings', type: 'nav', label: 'Settings', description: 'Profile and preferences', href: '/settings/profile', icon: 'settings' },
]

function ResultIcon({ result }: { result: SearchResult }) {
  const cls = 'w-4 h-4 flex-shrink-0'
  if (result.type === 'scan') {
    if (result.verdict === 'human') return <CheckCircle2 className={cn(cls, 'text-human')} />
    if (result.verdict === 'ai_generated') return <AlertTriangle className={cn(cls, 'text-ai')} />
    return <UncertainIcon className={cn(cls, 'text-uncertain')} />
  }
  const iconMap: Record<string, React.ReactNode> = {
    upload: <Upload className={cn(cls, 'text-brand')} />,
    dashboard: <LayoutDashboard className={cn(cls, 'text-text-secondary')} />,
    clock: <Clock className={cn(cls, 'text-text-secondary')} />,
    help: <HelpCircle className={cn(cls, 'text-text-secondary')} />,
    message: <MessageSquare className={cn(cls, 'text-text-secondary')} />,
    settings: <Settings className={cn(cls, 'text-text-secondary')} />,
  }
  return <>{iconMap[result.icon ?? ''] ?? <ArrowRight className={cn(cls, 'text-text-tertiary')} />}</>
}

export function GlobalSearch() {
  const isOpen = useUIStore((s) => s.searchOpen)
  const setOpen = useUIStore((s) => s.setSearchOpen)
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [activeIdx, setActiveIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  // Open with Cmd/Ctrl + K
  useKeyboard([
    {
      key: 'k',
      mods: ['meta'],
      onPress: () => setOpen(!isOpen),
    },
    {
      key: 'k',
      mods: ['ctrl'],
      onPress: () => setOpen(!isOpen),
    },
  ])

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setActiveIdx(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  const close = useCallback(() => {
    setOpen(false)
    setQuery('')
  }, [setOpen])

  // Real scan content, searched by filename — only fetched while the
  // palette is open, and only once (react-query caches it for the session).
  const { data: recentScans } = useQuery({
    queryKey: ['search-recent-scans'],
    queryFn: fetchRecentScans,
    enabled: isOpen,
    staleTime: 60_000,
  })

  const scanResults: SearchResult[] = useMemo(
    () =>
      (recentScans ?? []).map((scan) => ({
        id: `scan-${scan.scan_id}`,
        type: 'scan' as const,
        label: scan.file_name,
        description: `${scan.verdict === 'ai_generated' ? 'AI Generated' : scan.verdict === 'human' ? 'Human' : 'Uncertain'} · ${Math.round(scan.confidence)}%`,
        href: `/scan/${scan.scan_id}`,
        verdict: scan.verdict,
      })),
    [recentScans]
  )

  const results = query.trim()
    ? [...QUICK_ACTIONS, ...scanResults].filter(
        (r) =>
          r.label.toLowerCase().includes(query.toLowerCase()) ||
          (r.description?.toLowerCase().includes(query.toLowerCase()))
      )
    : QUICK_ACTIONS

  const handleSelect = useCallback(
    (result: SearchResult) => {
      close()
      navigate(result.href)
    },
    [close, navigate]
  )

  // Arrow key navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') { close(); return }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIdx((i) => Math.min(i + 1, results.length - 1))
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIdx((i) => Math.max(i - 1, 0))
    }
    if (e.key === 'Enter' && results[activeIdx]) {
      handleSelect(results[activeIdx])
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            key="search-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
            onClick={close}
            aria-hidden="true"
          />

          {/* Dialog */}
          <motion.div
            key="search-dialog"
            initial={{ opacity: 0, scale: 0.97, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: -8 }}
            transition={{ duration: 0.18, ease: [0.25, 0, 0, 1] }}
            className="fixed left-1/2 top-[15%] z-50 -translate-x-1/2 w-full max-w-xl mx-4"
            role="dialog"
            aria-label="Search"
            aria-modal="true"
          >
            <div className="rounded-2xl bg-bg-elevated border border-chrome/10 shadow-elevated overflow-hidden">
              {/* Search input */}
              <div className="flex items-center gap-3 px-4 py-3.5 border-b border-chrome/6">
                <Search className="w-4 h-4 text-text-tertiary flex-shrink-0" aria-hidden="true" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => { setQuery(e.target.value); setActiveIdx(0) }}
                  onKeyDown={handleKeyDown}
                  placeholder="Search or jump to…"
                  className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none"
                  aria-label="Search VoiceGuard"
                  aria-autocomplete="list"
                  aria-controls="search-results"
                  role="combobox"
                  aria-expanded="true"
                  aria-activedescendant={results[activeIdx] ? `search-result-${results[activeIdx].id}` : undefined}
                />
                {query && (
                  <button
                    onClick={() => setQuery('')}
                    className="text-text-tertiary hover:text-text-secondary transition-colors"
                    aria-label="Clear search"
                  >
                    <X className="w-4 h-4" aria-hidden="true" />
                  </button>
                )}
                <button
                  onClick={close}
                  className="px-2 py-1 rounded-md border border-chrome/10 text-[10px] font-medium text-text-tertiary hover:text-text-secondary transition-colors"
                  aria-label="Close search (Escape)"
                >
                  ESC
                </button>
              </div>

              {/* Results */}
              <div
                id="search-results"
                role="listbox"
                aria-label="Search results"
                className="py-2 max-h-[360px] overflow-y-auto"
              >
                {results.length === 0 ? (
                  <div className="px-4 py-8 text-center text-sm text-text-tertiary">
                    No results for "{query}"
                  </div>
                ) : (
                  <>
                    {!query && (
                      <p className="px-4 py-1 text-[10px] font-semibold text-text-tertiary uppercase tracking-widest">
                        Quick actions
                      </p>
                    )}
                    {results.map((result, i) => (
                      <div
                        key={result.id}
                        id={`search-result-${result.id}`}
                        role="option"
                        aria-selected={i === activeIdx}
                        className={cn(
                          'flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors',
                          i === activeIdx
                            ? 'bg-brand-muted/40'
                            : 'hover:bg-chrome/4'
                        )}
                        onClick={() => handleSelect(result)}
                        onMouseEnter={() => setActiveIdx(i)}
                      >
                        <div
                          className={cn(
                            'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                            result.type === 'action'
                              ? 'bg-brand-muted border border-brand-border'
                              : 'bg-chrome/5 border border-chrome/8'
                          )}
                        >
                          <ResultIcon result={result} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-text-primary truncate">
                            {result.label}
                          </p>
                          {result.description && (
                            <p className="text-xs text-text-tertiary truncate">
                              {result.description}
                            </p>
                          )}
                        </div>
                        {i === activeIdx && (
                          <ArrowRight className="w-3.5 h-3.5 text-brand flex-shrink-0" aria-hidden="true" />
                        )}
                      </div>
                    ))}
                  </>
                )}
              </div>

              {/* Footer hint */}
              <div className="flex items-center gap-4 px-4 py-2.5 border-t border-chrome/6">
                <div className="flex items-center gap-1.5 text-[10px] text-text-tertiary">
                  <Keyboard className="w-3 h-3" aria-hidden="true" />
                  <span>↑↓ navigate</span>
                </div>
                <div className="text-[10px] text-text-tertiary">↵ select</div>
                <div className="ml-auto text-[10px] text-text-tertiary">
                  <span className="font-mono">⌘K</span> to toggle
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
