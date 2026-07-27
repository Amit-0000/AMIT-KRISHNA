import { motion } from 'framer-motion'
import { AlertOctagon, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface UploadErrorStateProps {
  message: string
  onRetry: () => void
}

export function UploadErrorState({ message, onRetry }: UploadErrorStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, ease: [0.25, 0, 0, 1] }}
      className="flex flex-col items-center justify-center min-h-[300px] text-center px-6"
      role="alert"
      aria-live="assertive"
    >
      <div className="w-16 h-16 rounded-2xl bg-ai-muted border border-ai-border flex items-center justify-center mb-5">
        <AlertOctagon className="w-7 h-7 text-ai" aria-hidden="true" />
      </div>
      <h2 className="text-heading-lg font-bold text-text-primary mb-2">Upload Failed</h2>
      <p className="text-sm text-text-secondary max-w-sm leading-relaxed mb-6">{message}</p>
      <Button onClick={onRetry} variant="outline" className="gap-2">
        <RefreshCw className="w-4 h-4" aria-hidden="true" />
        Try Again
      </Button>
    </motion.div>
  )
}
