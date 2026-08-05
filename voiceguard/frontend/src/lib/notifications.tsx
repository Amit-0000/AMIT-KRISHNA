import { CheckCircle2, AlertTriangle, Info, Shield } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { NotificationType } from '@/types'

export const NOTIFICATION_TYPE_LABELS: Record<NotificationType, string> = {
  scan_complete: 'Scans',
  scan_failed: 'Scans',
  system: 'System',
  alert: 'Alerts',
  info: 'Info',
  feedback_thanks: 'Feedback',
}

export function NotifIcon({ type, className }: { type: NotificationType; className?: string }) {
  const cls = cn('w-4 h-4 flex-shrink-0', className)
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
