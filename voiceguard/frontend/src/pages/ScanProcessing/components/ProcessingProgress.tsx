import { motion } from 'framer-motion'

interface ProcessingProgressProps {
  progressPct: number
}

export function ProcessingProgress({ progressPct }: ProcessingProgressProps) {
  return (
    <div
      role="progressbar"
      aria-valuenow={progressPct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Analysis progress: ${progressPct} percent`}
      className="space-y-2"
    >
      {/* Label row */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-text-tertiary uppercase tracking-wider">
          Progress
        </span>
          <span className="text-xs font-semibold text-brand tabular-nums">
          {progressPct}%
        </span>
      </div>

      {/* Track */}
      <div className="h-1.5 bg-white/8 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-brand to-brand-light rounded-full"
          initial={{ width: '0%' }}
          animate={{ width: `${progressPct}%` }}
          transition={{ duration: 0.65, ease: [0.25, 0, 0, 1] }}
        />
      </div>
    </div>
  )
}
