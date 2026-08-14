import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Upload, ChevronRight, Lock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useInView } from '@/hooks/useInView'
import { useReducedMotion } from '@/hooks/useReducedMotion'

const WAVEFORM_HEIGHTS = [30, 60, 45, 80, 55, 70, 40, 90, 65, 50, 75, 35, 60, 85, 50, 45, 70, 55, 30, 65]

export function CTASection() {
  const [ref, inView] = useInView<HTMLDivElement>({ threshold: 0.2 })
  const reducedMotion = useReducedMotion()

  return (
    <section
      ref={ref}
      className="py-28 relative overflow-hidden"
      aria-labelledby="cta-heading"
    >
      {/* Background */}
      <div
        className="absolute inset-0 bg-gradient-to-br from-brand-muted/40 via-bg-base to-bg-base"
        aria-hidden="true"
      />
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            'radial-gradient(circle at 50% 50%, rgba(123,108,234,1) 0%, transparent 60%)',
        }}
        aria-hidden="true"
      />

      {/* Waveform decoration — respects prefers-reduced-motion */}
      <div
        className="absolute bottom-0 left-0 right-0 h-24 flex items-end justify-center gap-1 overflow-hidden opacity-20"
        aria-hidden="true"
      >
        {WAVEFORM_HEIGHTS.map((h, i) => (
          <motion.span
            key={i}
            className="waveform-bar bg-brand"
            style={{ height: `${h}%` }}
            animate={
              reducedMotion
                ? {}
                : {
                    scaleY: [1, 0.4 + Math.random() * 0.6, 1],
                  }
            }
            transition={
              reducedMotion
                ? {}
                : {
                    duration: 1.4 + (i % 5) * 0.2,
                    repeat: Infinity,
                    delay: i * 0.08,
                    ease: 'easeInOut',
                  }
            }
          />
        ))}
      </div>

      <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: [0.25, 0, 0, 1] }}
        >
          <p className="text-xs font-semibold text-brand uppercase tracking-widest mb-6">
            Free forever. No credit card.
          </p>
          <h2
            id="cta-heading"
            className="text-display-md sm:text-display-lg font-bold text-text-primary mb-6"
          >
            Is this audio real?{' '}
            <span className="text-gradient-brand">Find out now.</span>
          </h2>
          <p className="text-body-lg text-text-secondary max-w-xl mx-auto mb-10">
            Create a free account and upload your first audio file in
            seconds — save your history, get a per-segment breakdown, and
            share results with a link when you need to.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
            <Link to="/signup">
              <Button size="xl" className="w-full sm:w-auto gap-2 group">
                <Upload
                  className="w-5 h-5 transition-transform group-hover:-translate-y-0.5"
                  aria-hidden="true"
                />
                Analyze audio free
                <ChevronRight
                  className="w-4 h-4 transition-transform group-hover:translate-x-0.5"
                  aria-hidden="true"
                />
              </Button>
            </Link>
            <Link to="/login">
              <Button variant="secondary" size="xl" className="w-full sm:w-auto">
                Sign in to dashboard
              </Button>
            </Link>
          </div>

          <div className="flex items-center justify-center gap-2 text-sm text-text-tertiary">
            <Lock className="w-3.5 h-3.5 text-human/50 flex-shrink-0" aria-hidden="true" />
            Your audio is deleted within 60 seconds. Never stored. Never used for training.
          </div>
        </motion.div>
      </div>
    </section>
  )
}
