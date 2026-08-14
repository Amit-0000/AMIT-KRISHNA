import { motion } from 'framer-motion'
import { Layers, Activity, Eye, Database } from 'lucide-react'
import { useInView } from '@/hooks/useInView'

const TECH_SPECS = [
  { label: 'Architecture', value: 'LCNN', sub: 'Light CNN — 9 conv layers, max-feature-map activation' },
  { label: 'Training data', value: 'ASVspoof 2019 LA', sub: '2,580 genuine + 22,800 spoofed utterances' },
  { label: 'Equal Error Rate', value: '7.07%', sub: 'On ASVspoof 2019 LA evaluation set' },
  { label: 'Parameters', value: '699,938', sub: '~2.8 MB model weight file' },
  { label: 'Input', value: 'Log Power Spectrum', sub: 'STFT: 25ms frame, 10ms shift, FFT-512' },
  { label: 'Inference', value: '3-second segments', sub: '1.5-second hop; multi-segment aggregation' },
]

const PIPELINE_STEPS = [
  { icon: Activity, label: 'Audio → LPS', desc: 'STFT with Hamming window converts raw audio to Log Power Spectrum' },
  { icon: Layers, label: 'LCNN forward pass', desc: '9 convolutional layers with Max-Feature-Map activation extract artifact features' },
  { icon: Eye, label: 'Grad-CAM', desc: 'Gradient-weighted class activation maps from features[9] layer highlight suspicious frequencies' },
  { icon: Database, label: 'Segment aggregation', desc: 'Scores from all 3-second segments are averaged into the final verdict; the most influential segments are surfaced in the result explanation' },
]

export function TechnologySection() {
  const [ref, inView] = useInView<HTMLDivElement>({ threshold: 0.08 })

  return (
    <section
      id="technology"
      ref={ref}
      className="py-28 scroll-mt-20"
      aria-labelledby="technology-heading"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-start">
          {/* Left: copy + pipeline */}
          <div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, ease: [0.25, 0, 0, 1] }}
            >
              <p className="text-xs font-semibold text-brand uppercase tracking-widest mb-4">
                Under the hood
              </p>
              <h2
                id="technology-heading"
                className="text-display-md font-bold text-text-primary mb-5"
              >
                Research-grade model,<br />production-grade speed
              </h2>
              <p className="text-body-md text-text-secondary leading-relaxed mb-10">
                VoiceGuard uses LCNN (Light Convolutional Neural Network) —
                the same architecture that topped the ASVspoof 2019 challenge
                leaderboard. The model runs entirely on CPU, keeping inference
                fast and infrastructure simple.
              </p>
            </motion.div>

            {/* Inference pipeline */}
            <div className="space-y-4" role="list" aria-label="Inference pipeline steps">
              {PIPELINE_STEPS.map((step, i) => {
                const Icon = step.icon
                return (
                  <motion.div
                    key={step.label}
                    role="listitem"
                    initial={{ opacity: 0, x: -16 }}
                    animate={inView ? { opacity: 1, x: 0 } : {}}
                    transition={{ duration: 0.4, delay: 0.1 + i * 0.1, ease: [0.25, 0, 0, 1] }}
                    className="flex gap-4 items-start p-4 rounded-xl bg-bg-surface border border-chrome/6"
                  >
                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-brand-muted border border-brand-border flex items-center justify-center mt-0.5">
                      <Icon className="w-4 h-4 text-brand" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-text-primary mb-1">{step.label}</p>
                      <p className="text-xs text-text-secondary leading-relaxed">{step.desc}</p>
                    </div>
                    <div className="flex-shrink-0 text-xs text-text-tertiary font-mono mt-0.5">
                      {String(i + 1).padStart(2, '0')}
                    </div>
                  </motion.div>
                )
              })}
            </div>
          </div>

          {/* Right: spec grid */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.2, ease: [0.25, 0, 0, 1] }}
          >
            <div className="rounded-2xl border border-chrome/8 bg-bg-surface overflow-hidden">
              <div className="px-6 py-4 border-b border-chrome/6 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-ai" aria-hidden="true" />
                <div className="w-2 h-2 rounded-full bg-uncertain" aria-hidden="true" />
                <div className="w-2 h-2 rounded-full bg-human" aria-hidden="true" />
                <span className="ml-2 text-xs text-text-tertiary font-mono">
                  model_card.json · LCNN v2.1.0
                </span>
              </div>
              <div className="divide-y divide-chrome/6" role="list" aria-label="Model specifications">
                {TECH_SPECS.map((spec, i) => (
                  <motion.div
                    key={spec.label}
                    role="listitem"
                    initial={{ opacity: 0 }}
                    animate={inView ? { opacity: 1 } : {}}
                    transition={{ duration: 0.3, delay: 0.3 + i * 0.06, ease: [0.25, 0, 0, 1] }}
                    className="px-6 py-4 flex items-start justify-between gap-6"
                  >
                    <div>
                      <p className="text-xs text-text-tertiary mb-0.5">{spec.label}</p>
                      <p className="text-xs text-text-tertiary/60">{spec.sub}</p>
                    </div>
                    <p className="text-sm font-semibold text-text-primary text-right flex-shrink-0 font-mono">
                      {spec.value}
                    </p>
                  </motion.div>
                ))}
              </div>

              {/* Weakness disclosure */}
              <div className="px-6 py-4 border-t border-chrome/6 bg-uncertain-muted/40">
                <p className="text-xs font-semibold text-uncertain mb-1">Known limitation</p>
                <p className="text-xs text-text-secondary leading-relaxed">
                  Neural codec attacks (VALL-E style) achieve 36.8% EER on this model.
                  VoiceGuard discloses this on every scan result.
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
