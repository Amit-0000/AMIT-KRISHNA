import { motion } from 'framer-motion'
import { useInView } from '@/hooks/useInView'

const STATS = [
  { value: '7.07%', label: 'Equal Error Rate', sub: 'ASVspoof 2019 LA benchmark' },
  { value: '234ms', label: 'Avg. inference time', sub: 'Per audio segment' },
  { value: '< 60s', label: 'Audio retention', sub: 'Deleted after analysis' },
  { value: '699K', label: 'Model parameters', sub: 'LCNN architecture, ~2.8MB' },
]

const LOGOS = [
  'Journalists',
  'Forensic Analysts',
  'Cybersecurity Teams',
  'Content Moderators',
  'Legal Professionals',
  'Researchers',
]

export function SocialProofSection() {
  const [ref, inView] = useInView<HTMLDivElement>({ threshold: 0.15 })

  return (
    <section
      ref={ref}
      className="py-20 border-t border-chrome/6"
      aria-label="Platform statistics"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Stats grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 mb-16">
          {STATS.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 16 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: i * 0.08, ease: [0.25, 0, 0, 1] }}
              className="text-center"
            >
              <div className="text-display-sm font-bold text-gradient-brand mb-1 tabular-nums">
                {stat.value}
              </div>
              <div className="text-sm font-semibold text-text-primary mb-1">{stat.label}</div>
              <div className="text-xs text-text-tertiary">{stat.sub}</div>
            </motion.div>
          ))}
        </div>

        {/* Trust line */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.5, delay: 0.4, ease: [0.25, 0, 0, 1] }}
          className="flex flex-col items-center gap-6"
        >
          <p className="text-xs font-semibold text-text-tertiary uppercase tracking-widest">
            Trusted by professionals in
          </p>
          <div
            className="flex flex-wrap justify-center gap-3"
            role="list"
            aria-label="Professional user groups"
          >
            {LOGOS.map((label) => (
              <div
                key={label}
                role="listitem"
                className="px-4 py-2 rounded-full border border-chrome/8 bg-chrome/3 text-xs text-text-secondary font-medium"
              >
                {label}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  )
}
