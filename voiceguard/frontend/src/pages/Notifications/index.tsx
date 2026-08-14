import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, BellOff, CheckCheck, RefreshCw, X } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn, formatRelativeTime } from '@/lib/utils'
import { NotifIcon, NOTIFICATION_TYPE_LABELS } from '@/lib/notifications'
import { useNotifications } from './hooks/useNotifications'
import type { AppNotification } from '@/types'

type FilterTab = 'all' | 'unread' | 'read'

function NotificationsSkeleton() {
  return (
    <div className="card-base rounded-xl divide-y divide-chrome/6 overflow-hidden">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex gap-3 px-5 py-4">
          <Skeleton className="w-8 h-8 rounded-lg flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-1/3 rounded" />
            <Skeleton className="h-3 w-2/3 rounded" />
          </div>
        </div>
      ))}
    </div>
  )
}

function NotificationsErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="card-base rounded-xl p-10 text-center">
      <div className="w-12 h-12 rounded-2xl bg-ai-muted border border-ai-border flex items-center justify-center mx-auto mb-4">
        <AlertTriangle className="w-6 h-6 text-ai" aria-hidden="true" />
      </div>
      <p className="text-sm text-text-secondary mb-4">Failed to load notifications.</p>
      <Button variant="secondary" size="sm" onClick={onRetry} className="gap-2">
        <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
        Try again
      </Button>
    </div>
  )
}

function NotificationsEmptyState({ filter }: { filter: FilterTab }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[40vh] text-center px-6 py-16">
      <div className="w-16 h-16 rounded-2xl bg-chrome/5 border border-chrome/8 flex items-center justify-center mb-5">
        <BellOff className="w-7 h-7 text-text-tertiary" aria-hidden="true" />
      </div>
      <h2 className="text-heading-lg font-semibold text-text-primary mb-2">
        {filter === 'unread' ? "You're all caught up" : filter === 'read' ? 'No read notifications' : 'No notifications yet'}
      </h2>
      <p className="text-sm text-text-secondary max-w-sm">
        {filter === 'all'
          ? "Scan results, model updates, and account activity will show up here."
          : filter === 'unread'
          ? 'New notifications will appear here as they arrive.'
          : 'Notifications you’ve read will collect here.'}
      </p>
    </div>
  )
}

function NotificationRow({
  notif,
  onRead,
  onDelete,
}: {
  notif: AppNotification
  onRead: (id: string) => void
  onDelete: (id: string) => void
}) {
  const navigate = useNavigate()

  function handleClick() {
    if (!notif.read) onRead(notif.id)
    if (notif.action_url) navigate(notif.action_url)
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'flex gap-4 px-5 py-4 transition-colors',
        notif.action_url && 'cursor-pointer hover:bg-chrome/[0.02]',
        !notif.read && 'bg-brand-muted/20'
      )}
      onClick={notif.action_url ? handleClick : undefined}
      role={notif.action_url ? 'button' : undefined}
      tabIndex={notif.action_url ? 0 : undefined}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && notif.action_url) handleClick()
      }}
    >
      <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-chrome/5 border border-chrome/8 flex items-center justify-center mt-0.5">
        <NotifIcon type={notif.type} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-3">
          <p className={cn('text-sm font-medium', notif.read ? 'text-text-secondary' : 'text-text-primary')}>
            {notif.title}
          </p>
          <span className="text-xs text-text-tertiary whitespace-nowrap">{formatRelativeTime(notif.created_at)}</span>
        </div>
        <p className="text-sm text-text-tertiary mt-0.5">{notif.body}</p>
        <div className="flex items-center gap-2 mt-1.5">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary">
            {NOTIFICATION_TYPE_LABELS[notif.type]}
          </span>
          {!notif.read && (
            <span className="w-1.5 h-1.5 rounded-full bg-brand" aria-label="Unread" />
          )}
        </div>
      </div>
      <div className="flex-shrink-0 flex items-start gap-1">
        {!notif.read && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onRead(notif.id)
            }}
            className="self-start text-xs text-text-tertiary hover:text-brand transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded px-1.5 py-0.5"
          >
            Mark read
          </button>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete(notif.id)
          }}
          aria-label="Delete notification"
          className="self-start p-1 rounded text-text-tertiary hover:text-ai transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
        >
          <X className="w-3.5 h-3.5" aria-hidden="true" />
        </button>
      </div>
    </motion.div>
  )
}

const TABS: { value: FilterTab; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'unread', label: 'Unread' },
  { value: 'read', label: 'Read' },
]

export function NotificationsPage() {
  const { notifications, unreadCount, isLoading, isError, refetch, markRead, markAllRead, deleteNotification } =
    useNotifications()
  const [filter, setFilter] = useState<FilterTab>('all')

  const filtered = useMemo(() => {
    const sorted = [...notifications].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
    if (filter === 'unread') return sorted.filter((n) => !n.read)
    if (filter === 'read') return sorted.filter((n) => n.read)
    return sorted
  }, [notifications, filter])

  return (
    <PageContainer
      maxWidth="lg"
      title="Notifications"
      description="Scan results, account activity, and product updates."
      actions={
        unreadCount > 0 ? (
          <Button variant="secondary" size="sm" onClick={markAllRead} className="gap-2">
            <CheckCheck className="w-3.5 h-3.5" aria-hidden="true" />
            Mark all as read
          </Button>
        ) : undefined
      }
    >
      {/* Filter tabs */}
      <div
        role="tablist"
        aria-label="Filter notifications"
        className="flex items-center gap-1 p-1 mb-4 rounded-lg bg-chrome/5 border border-chrome/8 w-fit"
      >
        {TABS.map((tab) => (
          <button
            key={tab.value}
            role="tab"
            aria-selected={filter === tab.value}
            onClick={() => setFilter(tab.value)}
            className={cn(
              'px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
              filter === tab.value
                ? 'bg-brand text-white'
                : 'text-text-tertiary hover:text-text-secondary'
            )}
          >
            {tab.label}
            {tab.value === 'unread' && unreadCount > 0 && (
              <span className="ml-1.5 tabular-nums">{unreadCount}</span>
            )}
          </button>
        ))}
      </div>

      {isLoading ? (
        <NotificationsSkeleton />
      ) : isError ? (
        <NotificationsErrorState onRetry={refetch} />
      ) : filtered.length === 0 ? (
        <NotificationsEmptyState filter={filter} />
      ) : (
        <div className="card-base rounded-xl divide-y divide-chrome/6 overflow-hidden">
          <AnimatePresence initial={false} mode="popLayout">
            {filtered.map((notif) => (
              <NotificationRow key={notif.id} notif={notif} onRead={markRead} onDelete={deleteNotification} />
            ))}
          </AnimatePresence>
        </div>
      )}
    </PageContainer>
  )
}
