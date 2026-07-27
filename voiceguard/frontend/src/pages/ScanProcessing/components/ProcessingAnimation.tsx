import { motion } from 'framer-motion'

// Seven bars with staggered phases and heights produce a natural waveform pulse
const BARS = [
  { heights: [12, 36, 10, 32, 14], delay: 0.00 },
  { heights: [28, 10, 42, 18, 36], delay: 0.14 },
  { heights: [38, 24, 12, 40, 20], delay: 0.07 },
  { heights: [10, 36, 26, 10, 38], delay: 0.21 },
  { heights: [30, 14, 44, 22, 34], delay: 0.04 },
  { heights: [18, 42, 14, 36, 26], delay: 0.17 },
  { heights: [42, 20, 34, 16, 40], delay: 0.11 },
]

interface ProcessingAnimationProps {
  isActive: boolean
}

export function ProcessingAnimation({ isActive }: ProcessingAnimationProps) {
  return (
    <div
      className="flex items-center justify-center gap-1.5 h-16"
      aria-hidden="true"
    >
      {BARS.map((bar, i) => (
        <motion.div
          key={i}
          className="w-1.5 rounded-full bg-brand"
          animate={
            isActive
              ? {
                  height: bar.heights.map((h) => `${h}px`),
                  opacity: [0.55, 1, 0.6, 0.95, 0.6],
                }
              : { height: '4px', opacity: 0.18 }
          }
          transition={
            isActive
              ? {
                  duration: 1.5,
                  repeat: Infinity,
                  delay: bar.delay,
                  ease: 'easeInOut',
                }
              : { duration: 0.5, ease: [0.25, 0, 0, 1] }
          }
        />
      ))}
    </div>
  )
}
