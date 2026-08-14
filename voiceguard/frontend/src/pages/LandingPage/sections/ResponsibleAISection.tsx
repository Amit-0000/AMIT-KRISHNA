import { motion } from 'framer-motion'
import { Lock, UserX, AlertOctagon, BookOpen, Shield } from 'lucide-react'
import { useInView } from '@/hooks/useInView'

const PRINCIPLES = [
  {
    icon: Lock,
    title: 'Audio never stored permanently',
    description:
      'Your audio file is deleted within 60 seconds after inference completes. We store only the result (verdict, confidence, and the explanation). The audio bytes are never written to a database.',
    color: 'text-human',
    bg: 'bg-human-muted',
    border: 'border-human-border',
  },
  {
    icon: UserX,
    title: 'Audio never used as training data',
    description:
      'Submitted audio files are not used to train or fine-tune VoiceGuard\'s models. Only explicit user feedback (corrected verdicts) may contribute to future model versions.',
    color: 'text-brand',
    bg: 'bg-brand-muted',
    border: 'border-brand-border',
  },
  {
    icon: AlertOctagon,
    title: 'Limitations disclosed on every result',
    description:
      'Every scan result includes a limitations notice listing the model\'s known weaknesses — including the 36.8% EER on neural codec attacks. We never hide what the model doesn\'t know.',
    color: 'text-uncertain',
    bg: 'bg-uncertain-muted',
    border: 'border-uncertain-border',
  },
  {
    icon: BookOpen,
    title: 'Not legal evidence — we say so',
    description:
      'VoiceGuard results are an investigative aid, not legally admissible evidence. Every result carries an explicit advisory: "This analysis is for informational purposes only."',
    color: 'text-ai',
    bg: 'bg-ai-muted',
    border: 'border-ai-border',
  },
]

export function ResponsibleAISection() {
  const [ref, inView] = useInView<HTMLDivElement>({ threshold: 0.08 })

  return (
    <section
      id="responsible-ai"
      ref={ref}
      className="py-28 bg-bg-surface scroll-mt-20"
      aria-labelledby="responsible-ai-heading"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-start">
          {/* Left: copy */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, ease: [0.25, 0, 0, 1] }}
            className="lg:sticky lg:top-24"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-brand-muted border border-brand-border flex items-center justify-center">
                <Shield className="w-5 h-5 text-brand" aria-hidden="true" />
              </div>
              <p className="text-xs font-semibold text-brand uppercase tracking-widest">
                Responsible AI
              </p>
            </div>
            <h2
              id="responsible-ai-heading"
              className="text-display-md font-bold text-text-primary mb-6"
            >
              We earn your trust<br />by being honest first
            </h2>
            <p className="text-body-md text-text-secondary leading-relaxed mb-6">
              VoiceGuard's target users — journalists, forensic analysts, and
              security professionals — have been burned by overconfident AI
              tools. We build trust by leading with what the model doesn't know.
            </p>
            <p className="text-body-md text-text-secondary leading-relaxed">
              Every architectural decision — ephemeral audio storage, disclosed
              limitations, uncertain verdicts — exists because honesty is more
              valuable than the appearance of perfect accuracy.
            </p>
          </motion.div>

          {/* Right: principles */}
          <div className="space-y-4" role="list" aria-label="Responsible AI principles">
            {PRINCIPLES.map((p, i) => {
              const Icon = p.icon
              return (
                <motion.div
                  key={p.title}
                  role="listitem"
                  initial={{ opacity: 0, x: 16 }}
                  animate={inView ? { opacity: 1, x: 0 } : {}}
                  transition={{ duration: 0.45, delay: 0.1 + i * 0.1, ease: [0.25, 0, 0, 1] }}
                  className="card-base rounded-xl p-5 flex gap-4"
                >
                  <div
                    className={`flex-shrink-0 w-10 h-10 rounded-xl ${p.bg} border ${p.border} flex items-center justify-center mt-0.5`}
                  >
                    <Icon className={`w-5 h-5 ${p.color}`} aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="text-heading-sm text-text-primary mb-2">{p.title}</h3>
                    <p className="text-sm text-text-secondary leading-relaxed">{p.description}</p>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}
