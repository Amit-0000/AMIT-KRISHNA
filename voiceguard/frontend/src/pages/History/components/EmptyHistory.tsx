import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Upload, History as HistoryIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function EmptyHistory() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.25, 0, 0, 1] }}
      className="flex flex-col items-center justify-center min-h-[50vh] text-center px-6 py-16"
      aria-label="No scans yet"
    >
      <div className="w-20 h-20 rounded-3xl bg-brand-muted border border-brand-border flex items-center justify-center mb-8">
        <HistoryIcon className="w-9 h-9 text-brand" aria-hidden="true" />
      </div>

      <h2 className="text-display-sm font-bold text-text-primary mb-3">No scans yet</h2>
      <p className="text-body-md text-text-secondary max-w-sm leading-relaxed mb-8">
        Upload an audio file to start your first scan — you'll be able to track its
        progress and history here.
      </p>

      <Link to="/scan/new">
        <Button size="xl" className="gap-2">
          <Upload className="w-5 h-5" aria-hidden="true" />
          Upload your first file
        </Button>
      </Link>
    </motion.div>
  )
}
