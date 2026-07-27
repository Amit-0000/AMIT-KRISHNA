import { motion } from 'framer-motion'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface DashboardErrorStateProps {
  onRetry: () => void
}

export function DashboardErrorState({ onRetry }: DashboardErrorStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, ease: [0.25, 0, 0, 1] }}
      className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6"
      role="alert"
      aria-live="assertive"
    >
      <div className="w-16 h-16 rounded-2xl bg-ai-muted border border-ai-border flex items-center justify-center mb-6">
        <AlertTriangle className="w-8 h-8 text-ai" aria-hidden="true" />
      </div>

      <h2 className="text-display-sm font-bold text-text-primary mb-3">
        Failed to load dashboard
      </h2>
      <p className="text-sm text-text-secondary max-w-sm leading-relaxed mb-8">
        There was an error fetching your data. This is likely a temporary
        network issue. Please try again.
      </p>

      <Button onClick={onRetry} className="gap-2">
        <RefreshCw className="w-4 h-4" aria-hidden="true" />
        Retry
      </Button>
    </motion.div>
  )
}
