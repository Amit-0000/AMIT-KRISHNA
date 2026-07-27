import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  CheckCircle2,
  AlertTriangle,
  Info,
  Bell,
  BellOff,
  CheckCheck,
  Shield,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useUIStore } from '@/store/uiStore'
import { notificationApi } from '@/services/api'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { formatRelativeTime } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { AppNotification, NotificationType } from '@/types'

// ─── Seed mock data when no API available ────────────────────────────────────

const MOCK_NOTIFICATIONS: AppNotification[] = [
  {
    id: '1',
    type: 'scan_complete',
    title: 'Scan complete',
    body: 'voice_message.wav — AI Generated (91.4% confidence)',
    read: false,
    created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    action_url: '/history',
  },
  {
    id: '2',
    type: 'scan_complete',
    title: 'Scan complete',
    body: 'interview_audio.mp3 — Human (96.2% confidence)',
    read: false,
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    action_url: '/history',
  },
  {
    id: '3',
    type: 'system',
    title: 'Model updated',
    body: 'LCNN upgraded to v2.1.0. New: improved codec resistance.',
    read: true,
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: '4',
    type: 'feedback_thanks',
    title: 'Thanks for your feedback',
    body: 'Your correction helps improve future detections.',
    read: true,
    created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
  },
]

// ─── Icon per type ────────────────────────────────────────────────────────────

function NotifIcon({ type }: { type: NotificationType }) {
  const cls = 'w-4 h-4 flex-shrink-0'
  switch (type) {
    case 'scan_complete':
      return <CheckCircle2 className={cn(cls, 'text-human')} />
    case 'scan_failed':
      return <AlertTriangle className={cn(cls, 'text-ai')} />
    case 'alert':
      return <AlertTriangle className={cn(cls, 'text-uncertain')} />
    case 'feedback_thanks':
      return <Shield className={cn(cls, 'text-brand')} />
    case 'system':
      return <Info className={cn(cls, 'text-brand')} />
    default:
      return <Info className={cn(cls, 'text-text-secondary')} />
  }
}

// ─── Single item ──────────────────────────────────────────────────────────────

function NotifItem({
  notif,
  onRead,
}: {
  notif: AppNotification
  onRead: (id: string) => void
}) {
  const navigate = useNavigate()
  const setOpen = useUIStore((s) => s.setNotificationPanelOpen)

  const handleClick = () => {
    onRead(notif.id)
    if (notif.action_url) {
      navigate(notif.action_url)
      setOpen(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.22, ease: [0.25, 0, 0, 1] }}
      className={cn(
        'flex gap-3 px-4 py-3.5 transition-colors cursor-pointer',
        notif.action_url ? 'hover:bg-white/4' : 'cursor-default',
        !notif.read && 'bg-brand-muted/30'
      )}
      onClick={handleClick}
      role={notif.action_url ? 'button' : undefined}
      tabIndex={notif.action_url ? 0 : undefined}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') handleClick()
      }}
    >
      <div className="flex-shrink-0 mt-0.5">
        <NotifIcon type={notif.type} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 mb-0.5">
          <p
            className={cn(
              'text-sm font-medium truncate',
              notif.read ? 'text-text-secondary' : 'text-text-primary'
            )}
          >
            {notif.title}
          </p>
          {!notif.read && (
            <span
              className="w-1.5 h-1.5 rounded-full bg-brand flex-shrink-0"
              aria-label="Unread"
            />
          )}
        </div>
        <p className="text-xs text-text-tertiary leading-relaxed line-clamp-2">
          {notif.body}
        </p>
        <p className="text-[10px] text-text-tertiary mt-1">
          {formatRelativeTime(notif.created_at)}
        </p>
      </div>
    </motion.div>
  )
}

// ─── Panel ────────────────────────────────────────────────────────────────────

export function NotificationCenter() {
  const isOpen = useUIStore((s) => s.notificationPanelOpen)
  const setOpen = useUIStore((s) => s.setNotificationPanelOpen)
  const notifications = useUIStore((s) => s.notifications)
  const setNotifications = useUIStore((s) => s.setNotifications)
  const markRead = useUIStore((s) => s.markNotificationRead)
  const markAllRead = useUIStore((s) => s.markAllNotificationsRead)
  const unreadCount = useUIStore((s) => s.unreadCount)

  // Load notifications on open
  useEffect(() => {
    if (!isOpen) return
    if (notifications.length > 0) return
    notificationApi.list()
      .then(({ data }) => setNotifications(data))
      .catch(() => setNotifications(MOCK_NOTIFICATIONS))
  }, [isOpen, notifications.length, setNotifications])

  // Keyboard: Escape closes
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, setOpen])

  const handleMarkRead = async (id: string) => {
    markRead(id)
    try { await notificationApi.markRead(id) } catch { /* best-effort */ }
  }

  const handleMarkAllRead = async () => {
    markAllRead()
    try { await notificationApi.markAllRead() } catch { /* best-effort */ }
  }

  const isEmpty = notifications.length === 0

  return (
    <>
      {/* Backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            key="notif-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
        )}
      </AnimatePresence>

      {/* Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.aside
            key="notif-panel"
            initial={{ opacity: 0, x: 16, scale: 0.98 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 16, scale: 0.98 }}
            transition={{ duration: 0.22, ease: [0.25, 0, 0, 1] }}
            className="fixed right-4 top-[68px] z-50 w-[360px] rounded-2xl bg-bg-elevated border border-white/8 shadow-elevated overflow-hidden"
            role="dialog"
            aria-label="Notifications"
            aria-modal="false"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-4 border-b border-white/6">
              <div className="flex items-center gap-2">
                <Bell className="w-4 h-4 text-brand" aria-hidden="true" />
                <h2 className="text-sm font-semibold text-text-primary">Notifications</h2>
                {unreadCount > 0 && (
                  <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-brand text-[10px] font-bold text-white">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs text-text-tertiary hover:text-text-primary hover:bg-white/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                    aria-label="Mark all notifications as read"
                  >
                    <CheckCheck className="w-3.5 h-3.5" aria-hidden="true" />
                    All read
                  </button>
                )}
                <button
                  onClick={() => setOpen(false)}
                  className="flex items-center justify-center w-7 h-7 rounded-md text-text-tertiary hover:text-text-primary hover:bg-white/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                  aria-label="Close notifications"
                >
                  <X className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>
            </div>

            {/* Content */}
            <ScrollArea className="h-[420px]">
              {isEmpty ? (
                <div className="flex flex-col items-center justify-center h-40 gap-3 px-6">
                  <BellOff className="w-8 h-8 text-text-tertiary" aria-hidden="true" />
                  <p className="text-sm text-text-tertiary text-center">
                    No notifications yet. Scan results will appear here.
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-white/6">
                  {notifications.map((n) => (
                    <NotifItem key={n.id} notif={n} onRead={handleMarkRead} />
                  ))}
                </div>
              )}
            </ScrollArea>

            {/* Footer */}
            <div className="px-4 py-3 border-t border-white/6">
              <Button
                variant="ghost"
                size="sm"
                className="w-full text-text-tertiary hover:text-text-primary"
                onClick={() => {
                  setOpen(false)
                }}
                asChild
              >
                <a href="/notifications">View all notifications</a>
              </Button>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  )
}
