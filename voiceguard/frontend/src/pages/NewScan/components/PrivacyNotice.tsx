import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ShieldCheck, Lock, Clock, UserX, ChevronRight } from 'lucide-react'

const ITEMS = [
  { icon: Clock, text: 'Audio deleted within 60 seconds of analysis' },
  { icon: Lock, text: 'Never stored permanently on our servers' },
  { icon: UserX, text: 'Never used as training data — ever' },
]

export function PrivacyNotice() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, delay: 0.15, ease: [0.25, 0, 0, 1] }}
      className="rounded-xl border border-chrome/6 bg-chrome/[0.02] px-4 py-3.5"
    >
      <div className="flex items-start gap-3">
        <div className="w-7 h-7 rounded-lg bg-human-muted border border-human-border flex items-center justify-center flex-shrink-0 mt-0.5">
          <ShieldCheck className="w-3.5 h-3.5 text-human" aria-hidden="true" />
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-text-primary uppercase tracking-wider mb-2">
            Privacy Guarantee
          </p>

          <ul className="space-y-1.5 mb-2.5" role="list">
            {ITEMS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-2">
                <Icon className="w-3 h-3 text-human/60 flex-shrink-0" aria-hidden="true" />
                <span className="text-xs text-text-secondary">{text}</span>
              </li>
            ))}
          </ul>

          <Link
            to="/help"
            className="inline-flex items-center gap-1 text-xs text-text-tertiary hover:text-text-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
          >
            Learn more about how we handle your data
            <ChevronRight className="w-3 h-3" aria-hidden="true" />
          </Link>
        </div>
      </div>
    </motion.div>
  )
}
