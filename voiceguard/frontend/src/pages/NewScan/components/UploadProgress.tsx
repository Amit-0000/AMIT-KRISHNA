import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'

interface UploadProgressProps {
  progress: number
}

export function UploadProgress({ progress }: UploadProgressProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25, ease: [0.25, 0, 0, 1] }}
      className="card-base rounded-xl p-4 space-y-2.5"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Loader2 className="w-3.5 h-3.5 text-brand animate-spin flex-shrink-0" aria-hidden="true" />
          <span className="text-sm font-medium text-text-secondary">Uploading securely…</span>
        </div>
        <span
          className="text-sm font-semibold text-brand tabular-nums"
          aria-live="polite"
          aria-atomic="true"
        >
          {progress}%
        </span>
      </div>

      <div
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Upload progress: ${progress} percent`}
        className="h-1.5 bg-white/8 rounded-full overflow-hidden"
      >
        <motion.div
          className="h-full bg-gradient-to-r from-brand to-brand-light rounded-full"
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.25, ease: 'linear' }}
        />
      </div>

      <p className="text-xs text-text-tertiary">
        Do not close this tab — analysis begins immediately after upload.
      </p>
    </motion.div>
  )
}
