import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AlertOctagon, RefreshCw, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ProcessingErrorStateProps {
  message: string
  onRetry: () => void
}

export function ProcessingErrorState({ message, onRetry }: ProcessingErrorStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, ease: [0.25, 0, 0, 1] }}
      className="flex flex-col items-center text-center px-4 py-10"
      role="alert"
      aria-live="assertive"
    >
      <div className="w-16 h-16 rounded-2xl bg-ai-muted border border-ai-border flex items-center justify-center mb-5">
        <AlertOctagon className="w-7 h-7 text-ai" aria-hidden="true" />
      </div>

      <h2 className="text-heading-lg font-bold text-text-primary mb-2">
        Analysis Failed
      </h2>
      <p className="text-sm text-text-secondary max-w-xs leading-relaxed mb-7">
        {message}
      </p>

      <div className="flex flex-col sm:flex-row gap-3 w-full max-w-xs">
        <Button onClick={onRetry} className="flex-1 gap-2">
          <RefreshCw className="w-4 h-4" aria-hidden="true" />
          Retry
        </Button>
        <Button variant="secondary" asChild className="flex-1 gap-2">
          <Link to="/scan/new">
            <Upload className="w-4 h-4" aria-hidden="true" />
            New Upload
          </Link>
        </Button>
      </div>
    </motion.div>
  )
}
