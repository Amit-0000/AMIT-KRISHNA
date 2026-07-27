import { motion } from 'framer-motion'
import { CheckCircle2, AlertTriangle, HelpCircle, TrendingUp } from 'lucide-react'
import { useInView } from '@/hooks/useInView'
import { cn } from '@/lib/utils'

const VERDICTS = [
  {
    id: 'human',
    icon: CheckCircle2,
    label: 'Human / Genuine',
    confidence: 96.2,
    description:
      'Consistent micro-pitch variations and natural breath patterns detected. No neural synthesis artifacts in frequency spectrum.',
    language: 'Strong indicators of genuine human speech.',
    color: 'text-human',
    barColor: 'bg-human',
    bgColor: 'bg-human-muted',
    borderColor: 'border-human-border',
    glowClass: 'shadow-glow-human',
    threshold: '≥ 85% confidence',
  },
  {
    id: 'ai',
    icon: AlertTriangle,
    label: 'AI Generated',
    confidence: 91.4,
    description:
      'Uniform pitch stability, absence of natural prosody variation, and characteristic frequency artifacts at 3.2–4.8 kHz.',
    language: 'Strong indicators of neural voice synthesis.',
    color: 'text-ai',
    barColor: 'bg-ai',
    bgColor: 'bg-ai-muted',
    borderColor: 'border-ai-border',
    glowClass: 'shadow-glow-ai',
    threshold: '≥ 85% confidence',
  },
  {
    id: 'uncertain',
    icon: HelpCircle,
    label: 'Uncertain',
    confidence: 58.7,
    description:
      'Mixed signal characteristics. The audio may be post-processed, heavily compressed, or a voice conversion not in the training set.',
    language: 'Inconclusive — further analysis recommended.',
    color: 'text-uncertain',
    barColor: 'bg-uncertain',
    bgColor: 'bg-uncertain-muted',
    borderColor: 'border-uncertain-border',
    glowClass: '',
    threshold: '< 65% confidence',
  },
]

function VerdictCard({ verdict, index, inView }: {
  verdict: typeof VERDICTS[0]
  index: number
  inView: boolean
}) {
  const Icon = verdict.icon

  return (
    <motion.article
      initial={{ opacity: 0, y: 24 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay: 0.1 + index * 0.12, ease: [0.25, 0, 0, 1] }}
      className={cn(
        'card-base rounded-2xl p-6 flex flex-col gap-5',
        verdict.id === 'ai' && 'ring-1 ring-ai/20'
      )}
      aria-label={`${verdict.label} verdict — ${verdict.confidence}% confidence`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'w-10 h-10 rounded-xl flex items-center justify-center border',
              verdict.bgColor,
              verdict.borderColor
            )}
          >
            <Icon className={cn('w-5 h-5', verdict.color)} aria-hidden="true" />
          </div>
          <div>
            <h3 className={cn('text-heading-md font-bold', verdict.color)}>
              {verdict.label}
            </h3>
            <p className="text-xs text-text-tertiary">{verdict.threshold}</p>
          </div>
        </div>
        <TrendingUp className="w-4 h-4 text-text-tertiary" aria-hidden="true" />
      </div>

      {/* Confidence display */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-text-tertiary">Confidence</span>
          <span className={cn('text-2xl font-bold tabular-nums', verdict.color)}>
            {verdict.confidence}%
          </span>
        </div>
        <div
          className="h-2 rounded-full bg-white/6 overflow-hidden"
          role="progressbar"
          aria-valuenow={verdict.confidence}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Confidence: ${verdict.confidence}%`}
        >
          <motion.div
            className={cn('h-full rounded-full', verdict.barColor)}
            initial={{ width: '0%' }}
            animate={inView ? { width: `${verdict.confidence}%` } : { width: '0%' }}
            transition={{ duration: 1.2, delay: 0.3 + index * 0.12, ease: [0.25, 0, 0, 1] }}
          />
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-text-secondary leading-relaxed">
        {verdict.description}
      </p>

      {/* Verdict language */}
      <div
        className={cn(
          'px-4 py-3 rounded-lg border text-sm font-medium',
          verdict.bgColor,
          verdict.borderColor,
          verdict.color
        )}
      >
        "{verdict.language}"
      </div>
    </motion.article>
  )
}

export function VerdictShowcaseSection() {
  const [ref, inView] = useInView<HTMLDivElement>({ threshold: 0.1 })

  return (
    <section
      ref={ref}
      className="py-28 bg-bg-surface"
      aria-labelledby="verdicts-heading"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: [0.25, 0, 0, 1] }}
          className="text-center mb-16"
        >
          <p className="text-xs font-semibold text-brand uppercase tracking-widest mb-4">
            Three-state verdict system
          </p>
          <h2
            id="verdicts-heading"
            className="text-display-md font-bold text-text-primary mb-5"
          >
            Honest results, not overconfidence
          </h2>
          <p className="text-body-lg text-text-secondary max-w-2xl mx-auto">
            VoiceGuard uses calibrated confidence thresholds. When the model
            isn't sure, it says so — rather than forcing a binary answer that
            misleads you.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {VERDICTS.map((verdict, i) => (
            <VerdictCard key={verdict.id} verdict={verdict} index={i} inView={inView} />
          ))}
        </div>

        {/* Threshold legend */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.5, delay: 0.5, ease: [0.25, 0, 0, 1] }}
          className="mt-10 flex flex-wrap justify-center gap-6 text-xs text-text-tertiary"
          aria-label="Confidence threshold legend"
        >
          <span>
            <span className="text-human font-medium">≥ 85%</span> → Definitive verdict
          </span>
          <span aria-hidden="true">·</span>
          <span>
            <span className="text-uncertain font-medium">65–84%</span> → Borderline (shows as definitive with caveats)
          </span>
          <span aria-hidden="true">·</span>
          <span>
            <span className="text-text-secondary font-medium">&lt; 65%</span> → Uncertain
          </span>
        </motion.div>
      </div>
    </section>
  )
}
