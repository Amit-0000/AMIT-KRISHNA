import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Shield, Lock, UserX, AlertOctagon, ChevronRight } from 'lucide-react'

const PROMISES = [
  { icon: Lock,         text: 'Audio deleted within 60 seconds' },
  { icon: UserX,        text: 'Never used as training data' },
  { icon: AlertOctagon, text: 'Limitations disclosed on every result' },
]

export function PrivacyCard() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2, ease: [0.25, 0, 0, 1] }}
      className="card-base rounded-xl p-4 border-human-border/30"
    >
      <div className="flex items-center gap-2 mb-3">
        <div className="w-7 h-7 rounded-lg bg-human-muted border border-human-border flex items-center justify-center flex-shrink-0">
          <Shield className="w-3.5 h-3.5 text-human" aria-hidden="true" />
        </div>
        <h2 className="text-heading-sm font-semibold text-text-primary">Your Privacy</h2>
      </div>

      <ul className="space-y-2 mb-3" role="list" aria-label="Privacy promises">
        {PROMISES.map(({ icon: Icon, text }) => (
          <li key={text} className="flex items-center gap-2">
            <Icon className="w-3.5 h-3.5 text-human/70 flex-shrink-0" aria-hidden="true" />
            <span className="text-xs text-text-secondary">{text}</span>
          </li>
        ))}
      </ul>

      <Link
        to="/help"
        className="inline-flex items-center gap-1 text-xs text-text-tertiary hover:text-text-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
      >
        Learn more about privacy
        <ChevronRight className="w-3 h-3" aria-hidden="true" />
      </Link>
    </motion.div>
  )
}
