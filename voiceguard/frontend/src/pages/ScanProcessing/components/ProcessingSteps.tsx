import { motion, AnimatePresence } from 'framer-motion'
import { Check, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

// ─── Step definitions ─────────────────────────────────────────────────────────

const STEPS = [
  {
    id: 'upload',
    label: 'File received',
    subLabel: 'Audio validated and queued for analysis',
  },
  {
    id: 'segment',
    label: 'Segmenting audio',
    subLabel: 'Splitting into 3-second overlapping frames',
  },
  {
    id: 'infer',
    label: 'Running LCNN model',
    subLabel: 'Deep learning inference on each segment',
  },
  {
    id: 'score',
    label: 'Computing confidence',
    subLabel: 'Aggregating per-segment verdicts',
  },
  {
    id: 'heatmap',
    label: 'Generating frequency map',
    subLabel: 'Building spectral visualization',
  },
  {
    id: 'verdict',
    label: 'Finalizing verdict',
    subLabel: 'Preparing your forensic result',
  },
]

// ─── Progress → active step mapping ──────────────────────────────────────────
// Step 0 is always completed — we arrived here after a successful upload.
// Returns the index of the currently active (in-progress) step.

function activeStepFor(pct: number): number {
  if (pct < 15)  return 1
  if (pct < 40)  return 2
  if (pct < 63)  return 3
  if (pct < 83)  return 4
  if (pct < 100) return 5
  return STEPS.length  // all done
}

// ─── Component ────────────────────────────────────────────────────────────────

interface ProcessingStepsProps {
  progressPct: number
  isCompleted: boolean
}

export function ProcessingSteps({ progressPct, isCompleted }: ProcessingStepsProps) {
  const activeIdx = isCompleted ? STEPS.length : activeStepFor(progressPct)

  return (
    <ol
      className="space-y-0.5"
      aria-label="Analysis steps"
    >
      {STEPS.map((step, idx) => {
        const isDone   = idx < activeIdx
        const isActive = idx === activeIdx && !isCompleted

        return (
          <motion.li
            key={step.id}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
              delay: idx * 0.04,
              duration: 0.3,
              ease: [0.25, 0, 0, 1],
            }}
            className="flex items-start gap-3 py-1.5"
            aria-label={`${step.label}: ${isDone ? 'completed' : isActive ? 'in progress' : 'pending'}`}
          >
            {/* Status icon */}
            <div className="flex-shrink-0 w-5 h-5 mt-0.5">
              {isDone ? (
                <motion.div
                  initial={{ scale: 0.4, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: 'spring', stiffness: 500, damping: 22 }}
                  className="w-5 h-5 rounded-full bg-human-muted border border-human-border flex items-center justify-center"
                >
                  <Check
                    className="w-2.5 h-2.5 text-human"
                    strokeWidth={3}
                    aria-hidden="true"
                  />
                </motion.div>
              ) : isActive ? (
                <div className="w-5 h-5 rounded-full bg-brand-muted border border-brand-border flex items-center justify-center">
                  <Loader2
                    className="w-3 h-3 text-brand animate-spin"
                    aria-hidden="true"
                  />
                </div>
              ) : (
                <div className="w-5 h-5 rounded-full border border-white/10 bg-white/[0.02]" />
              )}
            </div>

            {/* Text */}
            <div className="flex-1 min-w-0">
              <p
                className={cn(
                  'text-sm font-medium leading-tight transition-colors duration-300',
                  isDone
                    ? 'text-text-tertiary'
                    : isActive
                    ? 'text-text-primary'
                    : 'text-text-tertiary/60'
                )}
              >
                {step.label}
              </p>

              <AnimatePresence>
                {isActive && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="text-xs text-text-tertiary mt-0.5"
                  >
                    {step.subLabel}
                  </motion.p>
                )}
              </AnimatePresence>
            </div>
          </motion.li>
        )
      })}
    </ol>
  )
}
