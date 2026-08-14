import { motion } from 'framer-motion'
import { Upload, Cpu, ShieldCheck } from 'lucide-react'
import { useInView } from '@/hooks/useInView'

const STEPS = [
  {
    number: '01',
    icon: Upload,
    title: 'Upload your audio',
    description:
      'Drop any audio file (WAV, MP3, FLAC, OGG, M4A) up to 10MB. Create a free account to get started — your history and results are saved to it.',
    color: 'text-brand',
    bgColor: 'bg-brand-muted',
    borderColor: 'border-brand-border',
  },
  {
    number: '02',
    icon: Cpu,
    title: 'LCNN analyzes frequency patterns',
    description:
      'Our Light CNN model converts audio to Log Power Spectrum and analyzes frequency artifacts in 3-second segments. The model processes only feature vectors — never raw audio.',
    color: 'text-uncertain',
    bgColor: 'bg-uncertain-muted',
    borderColor: 'border-uncertain-border',
  },
  {
    number: '03',
    icon: ShieldCheck,
    title: 'Get your forensic verdict',
    description:
      'Receive a verdict (human / AI-generated / uncertain) with a confidence score, per-segment breakdown, and the specific audio regions that most influenced the decision.',
    color: 'text-human',
    bgColor: 'bg-human-muted',
    borderColor: 'border-human-border',
  },
]

export function HowItWorksSection() {
  const [ref, inView] = useInView<HTMLDivElement>({ threshold: 0.1 })

  return (
    <section
      id="how-it-works"
      ref={ref}
      className="py-28 scroll-mt-20"
      aria-labelledby="how-it-works-heading"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: [0.25, 0, 0, 1] }}
          className="text-center mb-20"
        >
          <p className="text-xs font-semibold text-brand uppercase tracking-widest mb-4">
            How it works
          </p>
          <h2
            id="how-it-works-heading"
            className="text-display-md font-bold text-text-primary mb-5"
          >
            Three steps to the truth
          </h2>
          <p className="text-body-lg text-text-secondary max-w-2xl mx-auto">
            VoiceGuard uses the same signal-processing techniques employed in
            academic speech forensics research, packaged for anyone to use.
          </p>
        </motion.div>

        {/* Steps */}
        <div className="relative">
          {/* Connector line */}
          <div
            className="hidden lg:block absolute top-[52px] left-[16.66%] right-[16.66%] h-px bg-gradient-to-r from-transparent via-chrome/10 to-transparent"
            aria-hidden="true"
          />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {STEPS.map((step, i) => {
              const Icon = step.icon
              return (
                <motion.div
                  key={step.number}
                  initial={{ opacity: 0, y: 24 }}
                  animate={inView ? { opacity: 1, y: 0 } : {}}
                  transition={{
                    duration: 0.5,
                    delay: 0.1 + i * 0.12,
                    ease: [0.25, 0, 0, 1],
                  }}
                  className="relative flex flex-col items-center text-center lg:items-start lg:text-left"
                  aria-label={`Step ${step.number}: ${step.title}`}
                >
                  {/* Icon + number */}
                  <div className="relative mb-6">
                    <div
                      className={`w-14 h-14 rounded-2xl ${step.bgColor} border ${step.borderColor} flex items-center justify-center`}
                    >
                      <Icon className={`w-6 h-6 ${step.color}`} aria-hidden="true" />
                    </div>
                    <span
                      className="absolute -top-2 -right-2 text-[10px] font-bold text-text-tertiary bg-bg-elevated border border-chrome/8 rounded-full w-6 h-6 flex items-center justify-center"
                      aria-hidden="true"
                    >
                      {step.number}
                    </span>
                  </div>

                  <h3 className="text-heading-lg text-text-primary mb-3">{step.title}</h3>
                  <p className="text-body-sm text-text-secondary leading-relaxed">
                    {step.description}
                  </p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}
