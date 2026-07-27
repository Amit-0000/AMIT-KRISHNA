import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Upload, Shield, Lock, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'

const FEATURES = [
  { icon: Shield, text: 'Forensic-grade verdict with confidence score' },
  { icon: Lock,   text: 'Audio deleted within 60 seconds — zero storage risk' },
  { icon: Zap,    text: 'Results in under 2 seconds per segment' },
]

export function EmptyDashboard() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.25, 0, 0, 1] }}
      className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6 py-16"
      aria-label="No analyses yet"
    >
      {/* Icon */}
      <div className="relative mb-8">
        <div className="w-20 h-20 rounded-3xl bg-brand-muted border border-brand-border flex items-center justify-center">
          <Upload className="w-9 h-9 text-brand" aria-hidden="true" />
        </div>
        <div
          className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-human border-2 border-bg-base"
          aria-hidden="true"
        />
      </div>

      <h2 className="text-display-sm font-bold text-text-primary mb-3">
        No analyses yet
      </h2>
      <p className="text-body-md text-text-secondary max-w-sm leading-relaxed mb-8">
        Upload your first audio file to get a forensic verdict —
        human or AI-generated — with frequency analysis.
      </p>

      <Link to="/scan/new">
        <Button size="xl" className="mb-8 gap-2">
          <Upload className="w-5 h-5" aria-hidden="true" />
          Analyze your first audio file
        </Button>
      </Link>

      <ul
        className="flex flex-col items-center gap-2.5 text-sm"
        role="list"
        aria-label="Platform features"
      >
        {FEATURES.map(({ icon: Icon, text }) => (
          <li key={text} className="flex items-center gap-2 text-text-secondary">
            <Icon className="w-4 h-4 text-text-tertiary flex-shrink-0" aria-hidden="true" />
            {text}
          </li>
        ))}
      </ul>
    </motion.div>
  )
}
