import { useState } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { motion } from 'framer-motion'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useResolvedTheme } from '@/hooks/useResolvedTheme'
import type { TrendDataPoint } from '../types'

type Period = '7d' | '14d' | '30d'

interface TooltipPayloadItem {
  dataKey: string
  value: number
  color: string
  name: string
}

interface CustomTooltipProps {
  active?: boolean
  payload?: TooltipPayloadItem[]
  label?: string
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null

  return (
    <div className="rounded-xl bg-bg-elevated border border-chrome/10 p-3 shadow-elevated min-w-[160px]">
      <p className="text-xs font-semibold text-text-primary mb-2">{label}</p>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ background: entry.color }}
              aria-hidden="true"
            />
            <span className="text-text-secondary capitalize">
              {entry.name.replace('_', ' ')}
            </span>
          </div>
          <span className="font-semibold text-text-primary tabular-nums">{entry.value}</span>
        </div>
      ))}
    </div>
  )
}

interface TrendChartProps {
  data: TrendDataPoint[] | undefined
  loading?: boolean
}

const PERIOD_LABELS: Record<Period, string> = {
  '7d': '7 days',
  '14d': '14 days',
  '30d': '30 days',
}

export function TrendChart({ data, loading = false }: TrendChartProps) {
  const [period, setPeriod] = useState<Period>('30d')
  const resolvedTheme = useResolvedTheme()
  // recharts takes literal color props (not Tailwind classes), so grid/tick
  // colors — which are theme-dependent, unlike the fixed verdict colors
  // below — are resolved here instead of via CSS variables.
  const gridColor = resolvedTheme === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(10,10,20,0.08)'
  const cursorColor = resolvedTheme === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(10,10,20,0.12)'
  const tickColor = resolvedTheme === 'dark' ? '#8B8BA7' : '#5A5A70'

  const periodData = data
    ? data.slice(period === '7d' ? -7 : period === '14d' ? -14 : 0)
    : []

  // Thin out x-axis labels to avoid overlap
  const tickInterval = period === '7d' ? 0 : period === '14d' ? 1 : 4

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1, ease: [0.25, 0, 0, 1] }}
      className="card-base rounded-xl p-5"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-heading-md font-semibold text-text-primary">Detection Trend</h2>
          <p className="text-xs text-text-tertiary mt-0.5">Scans over time by verdict</p>
        </div>
        <div
          className="flex items-center gap-1 p-1 rounded-lg bg-bg-base border border-chrome/8"
          role="radiogroup"
          aria-label="Time period"
        >
          {(Object.keys(PERIOD_LABELS) as Period[]).map((p) => (
            <button
              key={p}
              role="radio"
              aria-checked={period === p}
              onClick={() => setPeriod(p)}
              className={cn(
                'px-2.5 py-1 rounded-md text-xs font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                period === p
                  ? 'bg-brand-muted text-brand'
                  : 'text-text-tertiary hover:text-text-secondary'
              )}
            >
              {PERIOD_LABELS[p]}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <Skeleton className="w-full h-[240px] rounded-lg" />
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={periodData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
            <defs>
              <linearGradient id="gradAI" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#FF4F4F" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#FF4F4F" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradHuman" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#32D583" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#32D583" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradUncertain" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#F5A623" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#F5A623" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={gridColor}
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tick={{ fill: tickColor, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              interval={tickInterval}
            />
            <YAxis
              tick={{ fill: tickColor, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: cursorColor }} />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ paddingTop: '12px', fontSize: '11px', color: tickColor }}
              formatter={(value) => value.replace('_', ' ')}
            />
            <Area
              type="monotone"
              dataKey="ai_generated"
              name="ai_generated"
              stroke="#FF4F4F"
              strokeWidth={2}
              fill="url(#gradAI)"
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
            />
            <Area
              type="monotone"
              dataKey="human"
              name="human"
              stroke="#32D583"
              strokeWidth={2}
              fill="url(#gradHuman)"
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
            />
            <Area
              type="monotone"
              dataKey="uncertain"
              name="uncertain"
              stroke="#F5A623"
              strokeWidth={1.5}
              fill="url(#gradUncertain)"
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </motion.div>
  )
}
