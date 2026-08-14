import { useEffect, useState, useRef } from 'react'
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import { Shield, CheckCircle2, AlertTriangle, Clock } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { useReducedMotion } from '@/hooks/useReducedMotion'

const CONFIDENCE = 91.4

// Simplified illustrative confidence-per-segment data, left (start of clip) to right (end)
const HEATMAP_BANDS = [
  0.12, 0.18, 0.25, 0.35, 0.55, 0.72, 0.85, 0.91, 0.88, 0.80,
  0.68, 0.74, 0.82, 0.78, 0.65, 0.55, 0.45, 0.38, 0.28, 0.22,
  0.18, 0.25, 0.30, 0.35, 0.28, 0.22, 0.18, 0.15, 0.12, 0.10,
]

function viridisColor(t: number): string {
  // Simplified viridis colormap interpolation
  const r = Math.round(68 + (253 - 68) * t)
  const g = Math.round(1 + (231 - 1) * Math.pow(t, 0.6))
  const b = Math.round(84 + (37 - 84) * t)
  return `rgb(${r},${g},${b})`
}

export function ProductPreviewCard() {
  const reducedMotion = useReducedMotion()
  const cardRef = useRef<HTMLDivElement>(null)
  const [confidenceDisplayed, setConfidenceDisplayed] = useState(0)
  const [barVisible, setBarVisible] = useState(false)

  // Tilt effect on mouse move
  const rotateX = useMotionValue(0)
  const rotateY = useMotionValue(0)
  const springX = useSpring(rotateX, { stiffness: 200, damping: 30 })
  const springY = useSpring(rotateY, { stiffness: 200, damping: 30 })
  const shadowX = useTransform(springY, [-8, 8], [-10, 10])
  const shadowY = useTransform(springX, [-8, 8], [10, -10])
  const boxShadow = useTransform(
    [shadowX, shadowY],
    ([x, y]) => `${x as number}px ${y as number}px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.08)`
  )

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (reducedMotion) return
    const rect = cardRef.current?.getBoundingClientRect()
    if (!rect) return
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    const dx = (e.clientX - cx) / rect.width
    const dy = (e.clientY - cy) / rect.height
    rotateX.set(-dy * 8)
    rotateY.set(dx * 8)
  }

  const handleMouseLeave = () => {
    rotateX.set(0)
    rotateY.set(0)
  }

  // Animate confidence counter on mount
  useEffect(() => {
    if (reducedMotion) {
      setConfidenceDisplayed(CONFIDENCE)
      setBarVisible(true)
      return
    }
    const delay = setTimeout(() => {
      setBarVisible(true)
      let start = 0
      const step = CONFIDENCE / 60
      const interval = setInterval(() => {
        start += step
        if (start >= CONFIDENCE) {
          setConfidenceDisplayed(CONFIDENCE)
          clearInterval(interval)
        } else {
          setConfidenceDisplayed(parseFloat(start.toFixed(1)))
        }
      }, 16)
      return () => clearInterval(interval)
    }, 800)
    return () => clearTimeout(delay)
  }, [reducedMotion])

  return (
    <motion.div
      ref={cardRef}
      style={reducedMotion ? {} : { rotateX: springX, rotateY: springY, transformPerspective: 1200 }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="relative w-full max-w-[420px] mx-auto"
      aria-label="Example scan result: AI-generated audio detected with 91.4% confidence"
    >
      {/* Glow behind card */}
      <div
        className="absolute inset-0 rounded-2xl"
        style={{
          background: 'radial-gradient(ellipse at center, rgba(255, 79, 79, 0.15) 0%, transparent 70%)',
          filter: 'blur(24px)',
          transform: 'scale(1.1)',
        }}
        aria-hidden="true"
      />

      {/* Card */}
      <motion.div
        style={reducedMotion ? {} : { boxShadow }}
        className="relative rounded-2xl bg-bg-surface border border-chrome/8 overflow-hidden"
      >
        {/* Card header */}
        <div className="px-5 pt-5 pb-4 border-b border-chrome/6">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-brand" aria-hidden="true" />
              <span className="text-xs font-semibold text-text-secondary uppercase tracking-widest">
                Scan Result
              </span>
            </div>
            <Badge variant="neutral" className="text-[10px]">
              LCNN v2.1.0
            </Badge>
          </div>
          <p className="text-xs text-text-tertiary truncate mt-1">
            voice_message_unknown.wav · 8.3s
          </p>
        </div>

        {/* Verdict */}
        <div className="px-5 py-5">
          <div className="flex items-start gap-4 mb-6">
            <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-ai-muted border border-ai-border flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-ai" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-lg font-bold text-ai">AI Generated</h3>
              </div>
              <p className="text-xs text-text-secondary leading-relaxed">
                Strong indicators of neural voice synthesis detected.
              </p>
            </div>
          </div>

          {/* Confidence bar */}
          <div className="mb-5" role="group" aria-label="Confidence scores">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-text-tertiary font-medium">AI Score</span>
              <span className="text-xs font-bold text-ai tabular-nums">
                {confidenceDisplayed.toFixed(1)}%
              </span>
            </div>
            <div className="h-2 rounded-full bg-chrome/6 overflow-hidden" role="progressbar" aria-valuenow={confidenceDisplayed} aria-valuemin={0} aria-valuemax={100} aria-label={`AI confidence: ${confidenceDisplayed.toFixed(1)}%`}>
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-ai/70 to-ai"
                initial={{ width: '0%' }}
                animate={{ width: barVisible ? `${CONFIDENCE}%` : '0%' }}
                transition={{ duration: 1.4, ease: [0.25, 0, 0, 1], delay: reducedMotion ? 0 : 0.1 }}
              />
            </div>
            <div className="flex items-center justify-between mt-2">
              <span className="text-xs text-text-tertiary font-medium">Human Score</span>
              <span className="text-xs font-bold text-text-tertiary tabular-nums">
                {(100 - CONFIDENCE).toFixed(1)}%
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-chrome/6 overflow-hidden mt-1" role="progressbar" aria-valuenow={100 - CONFIDENCE} aria-valuemin={0} aria-valuemax={100} aria-label={`Human confidence: ${(100 - CONFIDENCE).toFixed(1)}%`}>
              <motion.div
                className="h-full rounded-full bg-human/50"
                initial={{ width: '0%' }}
                animate={{ width: barVisible ? `${(100 - CONFIDENCE)}%` : '0%' }}
                transition={{ duration: 1.4, ease: [0.25, 0, 0, 1], delay: reducedMotion ? 0 : 0.2 }}
              />
            </div>
          </div>

          {/* Most-influential-regions preview — mirrors the real ScanResult
              explanation panel's salient-region timeline, not a frequency
              heatmap (VoiceGuard doesn't produce one). */}
          <div className="rounded-lg overflow-hidden border border-chrome/6 mb-4">
            <div className="px-3 py-2 border-b border-chrome/6 flex items-center justify-between">
              <span className="text-[10px] font-semibold text-text-tertiary uppercase tracking-widest">
                Most Influential Regions
              </span>
              <span className="text-[10px] text-text-tertiary">Per-segment confidence</span>
            </div>
            <div className="relative h-20 bg-[#0a0a18]" aria-hidden="true">
              {/* Illustrative bars */}
              <div className="absolute inset-0 flex items-end pb-1 px-1 gap-[2px]">
                {HEATMAP_BANDS.map((intensity, i) => (
                  <motion.div
                    key={i}
                    className="flex-1 rounded-sm origin-bottom"
                    style={{ backgroundColor: viridisColor(intensity) }}
                    initial={{ scaleY: 0 }}
                    animate={{ scaleY: barVisible ? 0.2 + intensity * 0.8 : 0 }}
                    transition={{
                      duration: 0.6,
                      delay: reducedMotion ? 0 : 0.8 + i * 0.02,
                      ease: [0.25, 0, 0, 1],
                    }}
                  />
                ))}
              </div>
              {/* Timeline labels */}
              <div className="absolute bottom-1 left-2 text-[8px] text-chrome/30">0:00</div>
              <div className="absolute bottom-1 right-2 text-[8px] text-chrome/30">clip end</div>
            </div>
          </div>

          {/* Metadata row */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-1.5 text-[10px] text-text-tertiary">
              <Clock className="w-3 h-3" aria-hidden="true" />
              <span>234ms</span>
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-text-tertiary">
              <CheckCircle2 className="w-3 h-3 text-human/60" aria-hidden="true" />
              <span>4 segments analyzed</span>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
