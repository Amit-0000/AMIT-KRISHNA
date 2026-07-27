import { motion } from 'framer-motion'
import { Zap, X, AlertTriangle, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface UploadActionsProps {
  onAnalyze: () => void
  onCancel: () => void
  isUploading: boolean
  errorMessage: string | null
}

export function UploadActions({
  onAnalyze,
  onCancel,
  isUploading,
  errorMessage,
}: UploadActionsProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3, delay: 0.15, ease: [0.25, 0, 0, 1] }}
      className="space-y-3"
    >
      {/* Upload error inline notice */}
      {errorMessage && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start gap-2.5 rounded-xl border border-ai-border bg-ai-muted/30 px-4 py-3"
          role="alert"
          aria-live="polite"
        >
          <AlertTriangle
            className="w-4 h-4 text-ai flex-shrink-0 mt-0.5"
            aria-hidden="true"
          />
          <div className="flex-1">
            <p className="text-sm text-text-secondary">{errorMessage}</p>
          </div>
        </motion.div>
      )}

      {/* Primary + secondary CTA */}
      <div className="flex gap-3">
        <Button
          size="lg"
          onClick={onAnalyze}
          loading={isUploading}
          className="flex-1 h-12 text-[15px] gap-2"
          aria-label="Analyze audio for AI detection"
        >
          {!isUploading && (
            errorMessage ? (
              <RotateCcw className="w-4 h-4" aria-hidden="true" />
            ) : (
              <Zap className="w-4 h-4" aria-hidden="true" />
            )
          )}
          {errorMessage && !isUploading ? 'Retry Upload' : 'Analyze Audio'}
        </Button>

        <Button
          size="lg"
          variant="secondary"
          onClick={onCancel}
          className="h-12 px-5 gap-2"
          aria-label={isUploading ? 'Cancel upload' : 'Remove file'}
        >
          <X className="w-4 h-4" aria-hidden="true" />
          {isUploading ? 'Cancel' : 'Remove'}
        </Button>
      </div>

      {isUploading && (
        <p className="text-xs text-center text-text-tertiary">
          Uploading securely over HTTPS — analysis begins immediately after.
        </p>
      )}
    </motion.div>
  )
}
