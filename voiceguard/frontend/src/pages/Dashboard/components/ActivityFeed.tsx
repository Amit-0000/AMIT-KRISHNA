import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  CheckCircle2,
  AlertTriangle,
  MessageSquare,
  Cpu,
  UserPlus,
  HelpCircle,
} from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { formatRelativeTime } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { ActivityItem, ActivityType } from '../types'
import type { Verdict } from '@/types'

function itemIcon(type: ActivityType, verdict?: Verdict) {
  const cls = 'w-4 h-4 flex-shrink-0'
  if (type === 'scan_complete') {
    if (verdict === 'human') return <CheckCircle2 className={cn(cls, 'text-human')} />
    if (verdict === 'ai_generated') return <AlertTriangle className={cn(cls, 'text-ai')} />
    return <HelpCircle className={cn(cls, 'text-uncertain')} />
  }
  if (type === 'scan_failed') return <AlertTriangle className={cn(cls, 'text-ai')} />
  if (type === 'feedback_submitted') return <MessageSquare className={cn(cls, 'text-brand')} />
  if (type === 'model_updated') return <Cpu className={cn(cls, 'text-brand')} />
  if (type === 'account_created') return <UserPlus className={cn(cls, 'text-human')} />
  return <CheckCircle2 className={cn(cls, 'text-text-tertiary')} />
}

function itemBg(type: ActivityType, verdict?: Verdict) {
  if (type === 'scan_complete') {
    if (verdict === 'human') return 'bg-human-muted border-human-border'
    if (verdict === 'ai_generated') return 'bg-ai-muted border-ai-border'
    return 'bg-uncertain-muted border-uncertain-border'
  }
  if (type === 'scan_failed') return 'bg-ai-muted border-ai-border'
  return 'bg-brand-muted border-brand-border'
}

interface ActivityFeedProps {
  items: ActivityItem[] | undefined
  loading?: boolean
}

export function ActivityFeed({ items, loading = false }: ActivityFeedProps) {
  const navigate = useNavigate()

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.22, ease: [0.25, 0, 0, 1] }}
      className="card-base rounded-xl overflow-hidden"
    >
      <div className="px-5 py-4 border-b border-white/6">
        <h2 className="text-heading-md font-semibold text-text-primary">Recent Activity</h2>
        <p className="text-xs text-text-tertiary mt-0.5">Your last 10 events</p>
      </div>

      <ScrollArea className="h-[320px]">
        {loading ? (
          <div className="px-5 py-4 space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex gap-3">
                <Skeleton className="w-8 h-8 rounded-lg flex-shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="w-3/4 h-3.5 rounded" />
                  <Skeleton className="w-1/2 h-3 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : !items || items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 gap-3 px-6">
            <CheckCircle2 className="w-8 h-8 text-text-tertiary" aria-hidden="true" />
            <p className="text-sm text-text-tertiary text-center">
              No activity yet. Start by analyzing your first audio file.
            </p>
          </div>
        ) : (
          <ol className="relative px-5 py-4 space-y-1" aria-label="Activity timeline">
            {items.map((item, i) => (
              <motion.li
                key={item.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25, delay: i * 0.05, ease: [0.25, 0, 0, 1] }}
                className={cn(
                  'flex gap-3 py-3 rounded-lg px-2 transition-colors',
                  item.scan_id && 'hover:bg-white/3 cursor-pointer'
                )}
                onClick={() => {
                  if (item.scan_id) navigate(`/history/${item.scan_id}`)
                }}
                role={item.scan_id ? 'button' : undefined}
                tabIndex={item.scan_id ? 0 : undefined}
                onKeyDown={(e) => {
                  if ((e.key === 'Enter' || e.key === ' ') && item.scan_id) {
                    navigate(`/history/${item.scan_id}`)
                  }
                }}
                aria-label={item.scan_id ? `View ${item.title}` : undefined}
              >
                <div
                  className={cn(
                    'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center border',
                    itemBg(item.type, item.verdict)
                  )}
                >
                  {itemIcon(item.type, item.verdict)}
                </div>
                <div className="flex-1 min-w-0 pt-0.5">
                  <p className="text-sm font-medium text-text-primary leading-tight">
                    {item.title}
                  </p>
                  <p className="text-xs text-text-secondary mt-0.5 leading-relaxed line-clamp-2">
                    {item.description}
                  </p>
                  <p className="text-[10px] text-text-tertiary mt-1">
                    {formatRelativeTime(item.timestamp)}
                  </p>
                </div>
              </motion.li>
            ))}
          </ol>
        )}
      </ScrollArea>
    </motion.div>
  )
}
