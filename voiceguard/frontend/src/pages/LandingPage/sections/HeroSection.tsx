import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Upload, ChevronRight, Lock, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ProductPreviewCard } from '../components/ProductPreviewCard'
import { useReducedMotion } from '@/hooks/useReducedMotion'

const EASE = [0.25, 0, 0, 1] as const

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.1 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE } },
}

const WAVEFORM_HEIGHTS = [20, 45, 60, 35, 75, 55, 30, 65, 50, 40, 70, 45, 25, 55, 80, 60, 35, 50]

export function HeroSection() {
  const reducedMotion = useReducedMotion()

  return (
    <section
      className="relative min-h-screen flex items-center pt-24 pb-20 overflow-hidden"
      aria-label="Hero — VoiceGuard audio deepfake detection"
    >
      {/* Background glow */}
      <div className="hero-glow" aria-hidden="true" />

      {/* Grid pattern */}
      <div
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(123,108,234,1) 1px, transparent 1px), linear-gradient(90deg, rgba(123,108,234,1) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
        aria-hidden="true"
      />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center">
          {/* Left — Copy */}
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="text-center lg:text-left"
          >
            {/* Announcement badge */}
            <motion.div variants={itemVariants} className="mb-8">
              <Badge variant="default" className="text-xs gap-2 px-3 py-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-brand animate-pulse-brand" aria-hidden="true" />
                LCNN model · 7.07% EER · ASVspoof 2019 LA
              </Badge>
            </motion.div>

            {/* Headline */}
            <motion.h1
              variants={itemVariants}
              className="text-display-lg sm:text-display-xl font-bold text-text-primary leading-[1.05] tracking-tight mb-6"
            >
              Detect AI voices{' '}
              <br className="hidden sm:block" />
              <span className="text-gradient-brand">in seconds.</span>
              <br />
              <span className="text-text-secondary font-normal text-display-md sm:text-display-lg">
                Free forever.
              </span>
            </motion.h1>

            {/* Subheadline */}
            <motion.p
              variants={itemVariants}
              className="text-body-lg text-text-secondary leading-relaxed mb-10 max-w-xl mx-auto lg:mx-0"
            >
              Upload any audio file and get a forensic-grade verdict — human or
              AI-generated — with confidence scores and frequency analysis.
              Your audio is deleted within 60 seconds.
            </motion.p>

            {/* CTAs */}
            <motion.div
              variants={itemVariants}
              className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start"
            >
              <Link to="/signup">
                <Button size="xl" className="w-full sm:w-auto gap-2 group">
                  <Upload className="w-5 h-5 transition-transform group-hover:-translate-y-0.5" aria-hidden="true" />
                  Analyze audio free
                  <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                </Button>
              </Link>
              <Link to="/login">
                <Button variant="secondary" size="xl" className="w-full sm:w-auto">
                  Sign in
                </Button>
              </Link>
            </motion.div>

            {/* Trust signals */}
            <motion.div
              variants={itemVariants}
              className="flex flex-col sm:flex-row items-center gap-5 mt-8 justify-center lg:justify-start"
            >
              <div className="flex items-center gap-2 text-sm text-text-tertiary">
                <Lock className="w-3.5 h-3.5 text-human/60 flex-shrink-0" aria-hidden="true" />
                Audio never stored permanently
              </div>
              <div className="hidden sm:block w-px h-4 bg-chrome/10" aria-hidden="true" />
              <div className="flex items-center gap-2 text-sm text-text-tertiary">
                <Zap className="w-3.5 h-3.5 text-brand/60 flex-shrink-0" aria-hidden="true" />
                Results in under 2 seconds
              </div>
            </motion.div>

            {/* Waveform decoration */}
            <motion.div
              variants={itemVariants}
              className="hidden lg:flex items-end gap-1 mt-12 h-10"
              aria-hidden="true"
            >
              {WAVEFORM_HEIGHTS.map((h, i) => (
                <motion.span
                  key={i}
                  className="waveform-bar bg-brand/20"
                  style={{ height: `${h}%` }}
                  animate={
                    reducedMotion
                      ? {}
                      : {
                          scaleY: [1, 0.3 + Math.random() * 0.7, 1],
                          transition: {
                            duration: 1.2 + Math.random() * 0.8,
                            repeat: Infinity,
                            delay: i * 0.06,
                            ease: 'easeInOut',
                          },
                        }
                  }
                />
              ))}
            </motion.div>
          </motion.div>

          {/* Right — Product preview */}
          <motion.div
            initial={{ opacity: 0, x: 40, scale: 0.96 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            transition={{ duration: 0.7, delay: 0.3, ease: EASE }}
            className="flex justify-center lg:justify-end"
          >
            <ProductPreviewCard />
          </motion.div>
        </div>
      </div>
    </section>
  )
}
