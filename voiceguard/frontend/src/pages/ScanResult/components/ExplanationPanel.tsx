import { motion } from 'framer-motion'
import { AlertTriangle, Info } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import type { AIScanExplanation } from '@/types'

function fmtTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = (seconds % 60).toFixed(1)
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

export function ExplanationPanel({
  explanation,
  isLoading,
}: {
  explanation?: AIScanExplanation
  isLoading: boolean
}) {
  if (isLoading || !explanation) {
    return (
      <div className="card-base rounded-xl p-5 space-y-3">
        <Skeleton className="h-4 rounded w-1/3" />
        <Skeleton className="h-4 rounded" />
        <Skeleton className="h-4 rounded" />
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.05 }}
      className="card-base rounded-xl p-5"
    >
      <h2 className="text-heading-md font-semibold text-text-primary mb-3">Explanation</h2>

      <ul className="space-y-2 mb-4">
        {explanation.notes.map((note, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-text-secondary">
            <Info className="w-4 h-4 mt-0.5 flex-shrink-0 text-brand" aria-hidden="true" />
            {note}
          </li>
        ))}
      </ul>

      {explanation.warnings.length > 0 && (
        <ul className="space-y-2 mb-4">
          {explanation.warnings.map((warning, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-uncertain">
              <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
              {warning}
            </li>
          ))}
        </ul>
      )}

      {explanation.salient_regions.length > 0 && (
        <div className="pt-3 border-t border-white/6">
          <h3 className="text-xs uppercase tracking-wider text-text-tertiary mb-2">
            Most influential audio regions
          </h3>
          <div className="space-y-1.5">
            {explanation.salient_regions.map((region, i) => (
              <div key={i} className="flex items-center gap-3 text-xs">
                <span className="font-mono text-text-secondary tabular-nums w-28">
                  {fmtTime(region.start_s)} – {fmtTime(region.end_s)}
                </span>
                <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-brand"
                    style={{ width: `${Math.round(region.importance * 100)}%` }}
                  />
                </div>
                <span className="text-text-tertiary tabular-nums w-10 text-right">
                  {Math.round(region.importance * 100)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="mt-4 text-[11px] text-text-tertiary">
        Feature set {explanation.feature_extractor} · Model {explanation.model_version}
      </p>
    </motion.div>
  )
}
