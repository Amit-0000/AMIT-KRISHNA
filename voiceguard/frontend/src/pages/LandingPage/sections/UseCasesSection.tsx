import { motion } from 'framer-motion'
import { Newspaper, Scale, Shield, Video, Mic, Users } from 'lucide-react'
import { useInView } from '@/hooks/useInView'
import { cn } from '@/lib/utils'

const USE_CASES = [
  {
    icon: Newspaper,
    title: 'Journalism & Fact-checking',
    description:
      'Verify audio evidence before publication. Detect synthetic voices in leaked recordings, political statements, or anonymous sources.',
    audience: 'Journalists · Editors · Fact-checkers',
    featured: true,
  },
  {
    icon: Scale,
    title: 'Legal & Forensics',
    description:
      'Pre-screen audio exhibits for AI synthesis indicators before commissioning formal forensic analysis.',
    audience: 'Attorneys · Expert witnesses · Courts',
    featured: false,
  },
  {
    icon: Shield,
    title: 'Cybersecurity',
    description:
      'Detect voice-cloning attacks in social engineering attempts. Validate caller identity in security-sensitive contexts.',
    audience: 'Security teams · SOC analysts · CISOs',
    featured: false,
  },
  {
    icon: Video,
    title: 'Content Moderation',
    description:
      'Screen user-generated audio at scale for AI-synthesized voices before they reach your platform.',
    audience: 'Platform trust teams · Content ops',
    featured: false,
  },
  {
    icon: Mic,
    title: 'Media Authenticity',
    description:
      'Verify audio in podcasts, interviews, and broadcast content for publishers maintaining editorial standards.',
    audience: 'Broadcasters · Podcast networks',
    featured: false,
  },
  {
    icon: Users,
    title: 'Security Research',
    description:
      'Evaluate voice deepfake detection capabilities and benchmark against known synthesis techniques.',
    audience: 'Researchers · Red teams · Academics',
    featured: false,
  },
]

export function UseCasesSection() {
  const [ref, inView] = useInView<HTMLDivElement>({ threshold: 0.08 })

  return (
    <section
      id="use-cases"
      ref={ref}
      className="py-28 scroll-mt-20"
      aria-labelledby="use-cases-heading"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: [0.25, 0, 0, 1] }}
          className="text-center mb-16"
        >
          <p className="text-xs font-semibold text-brand uppercase tracking-widest mb-4">
            Use cases
          </p>
          <h2
            id="use-cases-heading"
            className="text-display-md font-bold text-text-primary mb-5"
          >
            Built for professionals<br />who need the truth
          </h2>
          <p className="text-body-lg text-text-secondary max-w-2xl mx-auto">
            VoiceGuard was designed for users who understand the stakes — not a
            general consumer tool, but a forensic aid for professionals working
            with audio authenticity.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {USE_CASES.map((uc, i) => {
            const Icon = uc.icon
            return (
              <motion.article
                key={uc.title}
                initial={{ opacity: 0, y: 20 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.45, delay: 0.05 + i * 0.07, ease: [0.25, 0, 0, 1] }}
                className={cn(
                  'card-base rounded-xl p-6',
                  uc.featured && 'ring-1 ring-brand/25 bg-gradient-to-br from-bg-surface to-brand-muted/30'
                )}
                aria-label={uc.title}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className={cn(
                      'w-9 h-9 rounded-lg flex items-center justify-center',
                      uc.featured
                        ? 'bg-brand-muted border border-brand-border'
                        : 'bg-white/5 border border-white/8'
                    )}
                  >
                    <Icon
                      className={cn('w-4 h-4', uc.featured ? 'text-brand' : 'text-text-secondary')}
                      aria-hidden="true"
                    />
                  </div>
                  {uc.featured && (
                    <span className="text-[10px] font-semibold text-brand uppercase tracking-widest bg-brand-muted border border-brand-border rounded-full px-2 py-0.5">
                      Primary use case
                    </span>
                  )}
                </div>
                <h3 className="text-heading-sm text-text-primary mb-2">{uc.title}</h3>
                <p className="text-sm text-text-secondary leading-relaxed mb-4">
                  {uc.description}
                </p>
                <p className="text-xs text-text-tertiary font-medium">{uc.audience}</p>
              </motion.article>
            )
          })}
        </div>
      </div>
    </section>
  )
}
