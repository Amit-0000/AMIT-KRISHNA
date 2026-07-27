import { motion } from 'framer-motion'
import { AlertTriangle, FileX, Clock, HardDrive } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ValidationError, ValidationErrorCode } from '../types'
import type { LucideIcon } from 'lucide-react'

const CODE_ICONS: Record<ValidationErrorCode, LucideIcon> = {
  type: FileX,
  size: HardDrive,
  duration: Clock,
  corrupt: AlertTriangle,
}

interface UploadValidationProps {
  errors: ValidationError[]
  onDismiss: () => void
}

export function UploadValidation({ errors, onDismiss }: UploadValidationProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.25, ease: [0.25, 0, 0, 1] }}
      role="alert"
      aria-live="assertive"
      className="rounded-xl border border-ai-border bg-ai-muted/30 p-4"
    >
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-ai-muted border border-ai-border flex items-center justify-center flex-shrink-0 mt-0.5">
          <AlertTriangle className="w-4 h-4 text-ai" aria-hidden="true" />
        </div>

        <div className="flex-1">
          <p className="text-sm font-semibold text-text-primary mb-2">
            {errors.length === 1 ? 'File not accepted' : `${errors.length} issues found`}
          </p>

          <ul className="space-y-1.5" role="list">
            {errors.map((err) => {
              const Icon = CODE_ICONS[err.code]
              return (
                <li key={err.code} className="flex items-start gap-2">
                  <Icon
                    className="w-3.5 h-3.5 text-ai/80 flex-shrink-0 mt-0.5"
                    aria-hidden="true"
                  />
                  <span className="text-sm text-text-secondary">{err.message}</span>
                </li>
              )
            })}
          </ul>

          <Button
            size="sm"
            variant="ghost"
            onClick={onDismiss}
            className="mt-3 h-7 px-3 text-xs text-text-secondary hover:text-text-primary"
          >
            Try a different file
          </Button>
        </div>
      </div>
    </motion.div>
  )
}
