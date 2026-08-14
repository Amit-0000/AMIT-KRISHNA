import { useCallback } from 'react'
import { motion } from 'framer-motion'
import { Play, Pause, Volume2, VolumeX, SkipBack } from 'lucide-react'
import { cn } from '@/lib/utils'
import { WaveformVisualizer } from './WaveformVisualizer'
import type { PlayerState } from '../types'

interface AudioPlayerProps {
  objectUrl: string | null
  player: PlayerState
  onToggle: () => void
  onSeekByFraction: (fraction: number) => void
  onSetVolume: (vol: number) => void
  onToggleMute: () => void
  onRestart: () => void
}

function fmt(s: number): string {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

export function AudioPlayer({
  objectUrl,
  player,
  onToggle,
  onSeekByFraction,
  onSetVolume,
  onToggleMute,
  onRestart,
}: AudioPlayerProps) {
  const progress = player.duration > 0 ? player.currentTime / player.duration : 0

  const handleTrackClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect()
      onSeekByFraction(Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)))
    },
    [onSeekByFraction]
  )

  const handleTrackKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (!player.duration) return
      const step = 0.05
      if (e.key === 'ArrowRight') { e.preventDefault(); onSeekByFraction(Math.min(1, progress + step)) }
      if (e.key === 'ArrowLeft')  { e.preventDefault(); onSeekByFraction(Math.max(0, progress - step)) }
      if (e.key === 'Home')       { e.preventDefault(); onSeekByFraction(0) }
      if (e.key === 'End')        { e.preventDefault(); onSeekByFraction(1) }
      if (e.key === ' ' || e.key === 'k') { e.preventDefault(); onToggle() }
    },
    [player.duration, progress, onSeekByFraction, onToggle]
  )

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3, delay: 0.1, ease: [0.25, 0, 0, 1] }}
      className="card-base rounded-xl p-4 space-y-3"
    >
      <p className="text-xs font-semibold text-text-tertiary uppercase tracking-wider">
        Preview
      </p>

      {/* Waveform */}
      <WaveformVisualizer
        objectUrl={objectUrl}
        currentTime={player.currentTime}
        duration={player.duration}
        onSeek={onSeekByFraction}
        isPlaying={player.isPlaying}
      />

      {/* Thin progress bar — keyboard-accessible seek */}
      <div
        role="slider"
        aria-label="Audio position"
        aria-valuenow={Math.round(player.currentTime)}
        aria-valuemin={0}
        aria-valuemax={Math.round(player.duration)}
        aria-valuetext={`${fmt(player.currentTime)} of ${fmt(player.duration)}`}
        tabIndex={0}
        className={cn(
          'relative h-1 rounded-full cursor-pointer',
          'bg-chrome/8',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-1 focus-visible:ring-offset-bg-surface'
        )}
        onClick={handleTrackClick}
        onKeyDown={handleTrackKeyDown}
      >
        <div
          className="absolute left-0 top-0 h-full bg-brand rounded-full"
          style={{ width: `${progress * 100}%` }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 bg-brand rounded-full shadow-glow-brand"
          style={{ left: `calc(${progress * 100}% - 5px)` }}
        />
      </div>

      {/* Controls row */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-text-tertiary tabular-nums w-8">
          {fmt(player.currentTime)}
        </span>

        <div className="flex items-center gap-2">
          {/* Restart */}
          <button
            onClick={onRestart}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-text-tertiary hover:text-text-secondary hover:bg-chrome/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            aria-label="Restart from beginning"
          >
            <SkipBack className="w-3.5 h-3.5" aria-hidden="true" />
          </button>

          {/* Play / Pause */}
          <button
            onClick={onToggle}
            className={cn(
              'w-10 h-10 rounded-xl flex items-center justify-center text-white',
              'bg-brand hover:bg-brand-light transition-all',
              'shadow-glow-brand hover:shadow-[0_0_20px_rgba(123,108,234,0.4)]',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-bg-base'
            )}
            aria-label={player.isPlaying ? 'Pause' : 'Play'}
          >
            {player.isPlaying ? (
              <Pause className="w-4 h-4" aria-hidden="true" />
            ) : (
              <Play className="w-4 h-4 ml-0.5" aria-hidden="true" />
            )}
          </button>

          {/* Mute */}
          <button
            onClick={onToggleMute}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-text-tertiary hover:text-text-secondary hover:bg-chrome/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            aria-label={player.isMuted ? 'Unmute' : 'Mute'}
          >
            {player.isMuted ? (
              <VolumeX className="w-3.5 h-3.5" aria-hidden="true" />
            ) : (
              <Volume2 className="w-3.5 h-3.5" aria-hidden="true" />
            )}
          </button>

          {/* Volume slider */}
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={player.isMuted ? 0 : player.volume}
            onChange={(e) => onSetVolume(parseFloat(e.target.value))}
            className="w-16 h-1 accent-brand cursor-pointer"
            aria-label="Volume"
          />
        </div>

        <span className="text-xs font-mono text-text-tertiary tabular-nums w-8 text-right">
          {fmt(player.duration)}
        </span>
      </div>
    </motion.div>
  )
}
