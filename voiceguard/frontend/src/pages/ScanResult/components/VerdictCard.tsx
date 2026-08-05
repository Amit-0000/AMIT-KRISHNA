import { motion } from 'framer-motion'
import { ShieldCheck, ShieldAlert, ShieldQuestion } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AIVerdict } from '@/types'

const VERDICT_CONFIG: Record<
  AIVerdict,
  { label: string; description: string; icon: typeof ShieldCheck; className: string; glow: string }
> = {
  human: {
    label: 'Likely human',
    description: 'This audio shows the characteristics of a genuine human recording.',
    icon: ShieldCheck,
    className: 'verdict-human',
    glow: 'shadow-glow-human',
  },
  ai_generated: {
    label: 'Likely AI-generated',
    description: 'This audio shows signals consistent with synthetic or deepfake generation.',
    icon: ShieldAlert,
    className: 'verdict-ai',
    glow: 'shadow-glow-ai',
  },
  uncertain: {
    label: 'Uncertain',
    description: "The model's confidence fell below the decision threshold — treat this result as inconclusive.",
    icon: ShieldQuestion,
    className: 'verdict-uncertain',
    glow: '',
  },
}

export function VerdictCard({ verdict, confidence }: { verdict: AIVerdict; confidence: number }) {
  const cfg = VERDICT_CONFIG[verdict]
  const Icon = cfg.icon

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.25, 0, 0, 1] }}
      className={cn('card-base rounded-2xl p-8 flex flex-col items-center text-center gap-4', cfg.glow)}
    >
      <div className={cn('w-16 h-16 rounded-full flex items-center justify-center border', cfg.className)}>
        <Icon className="w-8 h-8" aria-hidden="true" />
      </div>
      <div>
        <h1 className="text-display-sm font-bold text-text-primary">{cfg.label}</h1>
        <p className="mt-2 text-sm text-text-secondary max-w-md">{cfg.description}</p>
      </div>
      <div className="flex items-center gap-2 mt-2">
        <span className="text-xs uppercase tracking-wider text-text-tertiary">Confidence</span>
        <span className={cn('text-2xl font-bold tabular-nums', cfg.className.replace('verdict-', 'text-'))}>
          {Math.round(confidence * 100)}%
        </span>
      </div>
    </motion.div>
  )
}
