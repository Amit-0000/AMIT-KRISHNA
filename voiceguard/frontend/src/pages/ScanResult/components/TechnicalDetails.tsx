import { motion } from 'framer-motion'
import { Skeleton } from '@/components/ui/skeleton'
import type { AIScanTechnical } from '@/types'

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-chrome/5 last:border-0">
      <span className="text-xs text-text-tertiary">{label}</span>
      <span className="text-sm font-medium text-text-primary tabular-nums">{value}</span>
    </div>
  )
}

export function TechnicalDetails({ technical, isLoading }: { technical?: AIScanTechnical; isLoading: boolean }) {
  if (isLoading || !technical) {
    return (
      <div className="card-base rounded-xl p-5 space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-4 rounded" />
        ))}
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="card-base rounded-xl p-5"
    >
      <h2 className="text-heading-md font-semibold text-text-primary mb-3">Technical details</h2>
      <div>
        <Row label="Raw label" value={technical.label} />
        <Row label="Bonafide score" value={`${(technical.raw_bonafide_score * 100).toFixed(1)}%`} />
        <Row label="Spoof score" value={`${(technical.raw_spoof_score * 100).toFixed(1)}%`} />
        <Row label="Decision threshold" value={`${(technical.threshold_used * 100).toFixed(0)}%`} />
        <Row label="Below threshold" value={technical.is_below_threshold ? 'Yes' : 'No'} />
        <Row label="Feature extractor" value={`${technical.feature_extractor_name}:${technical.feature_extractor_version}`} />
        <Row label="Model" value={`${technical.model_name} (${technical.model_architecture}) ${technical.model_version}`} />
        <Row label="Total processing time" value={`${technical.processing_time_ms} ms`} />
        <Row label="Inference time" value={`${technical.inference_time_ms} ms`} />
      </div>

      {technical.stage_timings.length > 0 && (
        <div className="mt-4 pt-4 border-t border-chrome/6">
          <h3 className="text-xs uppercase tracking-wider text-text-tertiary mb-2">Pipeline stage timing</h3>
          <div className="space-y-1">
            {technical.stage_timings.map((t, i) => (
              <div key={`${t.stage}-${t.attempt}-${i}`} className="flex items-center justify-between text-xs">
                <span className="text-text-secondary">
                  {t.stage.replace(/_/g, ' ')}
                  {t.attempt > 1 && <span className="text-text-tertiary"> (attempt {t.attempt})</span>}
                </span>
                <span className={t.status === 'succeeded' ? 'text-human' : 'text-ai'}>{t.duration_ms} ms</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}
