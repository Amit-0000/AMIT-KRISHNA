import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { motion } from 'framer-motion'
import { Skeleton } from '@/components/ui/skeleton'
import { useResolvedTheme } from '@/hooks/useResolvedTheme'
import type { ConfidenceBucket } from '../types'

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{ value: number; payload: ConfidenceBucket }>
  label?: string
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null
  const bucket = payload[0].payload
  const zoneLabel =
    bucket.zone === 'uncertain'
      ? 'Uncertain zone'
      : bucket.zone === 'borderline'
      ? 'Borderline'
      : 'Definitive zone'

  return (
    <div className="rounded-xl bg-bg-elevated border border-chrome/10 p-3 shadow-elevated">
      <p className="text-xs font-semibold text-text-primary mb-1">{label}</p>
      <p className="text-xs text-text-secondary">{payload[0].value} scans</p>
      <p className="text-[10px] text-text-tertiary mt-1">{zoneLabel}</p>
    </div>
  )
}

function zoneColor(zone: ConfidenceBucket['zone']): string {
  switch (zone) {
    case 'uncertain':  return '#F5A623'
    case 'borderline': return '#7B6CEA'
    case 'definitive': return '#32D583'
  }
}

interface ConfidenceChartProps {
  data: ConfidenceBucket[] | undefined
  loading?: boolean
}

export function ConfidenceChart({ data, loading = false }: ConfidenceChartProps) {
  const resolvedTheme = useResolvedTheme()
  const gridColor = resolvedTheme === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(10,10,20,0.08)'
  const cursorFill = resolvedTheme === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(10,10,20,0.04)'
  const tickColor = resolvedTheme === 'dark' ? '#8B8BA7' : '#5A5A70'

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.18, ease: [0.25, 0, 0, 1] }}
      className="card-base rounded-xl p-5"
    >
      <div className="mb-5">
        <h2 className="text-heading-md font-semibold text-text-primary">Confidence Distribution</h2>
        <p className="text-xs text-text-tertiary mt-0.5">Number of scans per confidence range</p>
      </div>

      {loading ? (
        <Skeleton className="w-full h-[200px] rounded-lg" />
      ) : (
        <>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={gridColor}
                vertical={false}
              />
              <XAxis
                dataKey="range"
                tick={{ fill: tickColor, fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                interval={0}
                angle={-30}
                textAnchor="end"
                height={40}
              />
              <YAxis
                tick={{ fill: tickColor, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: cursorFill }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {data?.map((entry, i) => (
                  <Cell key={i} fill={zoneColor(entry.zone)} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          {/* Zone legend */}
          <div
            className="flex items-center justify-center gap-5 mt-4"
            role="list"
            aria-label="Confidence zone legend"
          >
            {[
              { label: 'Uncertain (<65%)', color: '#F5A623' },
              { label: 'Borderline (65–84%)', color: '#7B6CEA' },
              { label: 'Definitive (≥85%)', color: '#32D583' },
            ].map((z) => (
              <div key={z.label} role="listitem" className="flex items-center gap-1.5">
                <span
                  className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                  style={{ background: z.color }}
                  aria-hidden="true"
                />
                <span className="text-[10px] text-text-tertiary">{z.label}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </motion.div>
  )
}
