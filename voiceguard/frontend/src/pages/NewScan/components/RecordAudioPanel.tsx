import { motion } from 'framer-motion'
import { Mic, Square, Play, Pause, RotateCcw, Sparkles, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { RecorderState } from '../hooks/useAudioRecorder'
import { useAudioPlayer } from '../hooks/useAudioPlayer'

interface RecordAudioPanelProps {
  recorder: RecorderState
  onStart: () => void
  onStop: () => void
  onReRecord: () => void
  onOpenSettings: () => void
  onAnalyze: (file: File) => void
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
}

export function RecordAudioPanel({ recorder, onStart, onStop, onReRecord, onOpenSettings, onAnalyze }: RecordAudioPanelProps) {
  const { player, toggle } = useAudioPlayer(recorder.objectUrl)

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.4, ease: [0.25, 0, 0, 1] }}
      className="flex flex-col items-center justify-center min-h-[340px] rounded-2xl border-2 border-dashed border-chrome/10 bg-chrome/[0.02] px-8 py-10 text-center"
    >
      {(recorder.phase === 'idle' || recorder.phase === 'requesting-permission') && (
        <>
          <div className="w-20 h-20 rounded-2xl flex items-center justify-center border border-chrome/8 bg-chrome/[0.04] mb-6">
            <Mic className="w-9 h-9 text-text-tertiary" aria-hidden="true" />
          </div>
          <p className="text-heading-sm font-semibold text-text-primary mb-1.5">Record with your microphone</p>
          <p className="text-sm text-text-secondary mb-6 max-w-xs">
            We'll ask for microphone permission the first time you record.
          </p>
          <button
            type="button"
            onClick={onStart}
            disabled={recorder.phase === 'requesting-permission'}
            className="inline-flex items-center gap-2 rounded-xl bg-brand px-5 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            <Mic className="w-4 h-4" aria-hidden="true" />
            {recorder.phase === 'requesting-permission' ? 'Requesting permission…' : 'Start Recording'}
          </button>
        </>
      )}

      {recorder.phase === 'permission-denied' && (
        <>
          <p className="text-heading-sm font-semibold text-text-primary mb-1.5">Microphone permission is required</p>
          <p className="text-sm text-text-secondary mb-6 max-w-xs">
            VoiceGuard needs microphone access to record audio for analysis.
          </p>
          <button
            type="button"
            onClick={onStart}
            className="inline-flex items-center gap-2 rounded-xl bg-brand px-5 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            Try Again
          </button>
        </>
      )}

      {recorder.phase === 'permission-denied-permanently' && (
        <>
          <p className="text-heading-sm font-semibold text-text-primary mb-1.5">Microphone permission is blocked</p>
          <p className="text-sm text-text-secondary mb-6 max-w-xs">
            Enable microphone access for VoiceGuard in Android Settings to record audio.
          </p>
          <button
            type="button"
            onClick={onOpenSettings}
            className="inline-flex items-center gap-2 rounded-xl bg-brand px-5 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            <Settings className="w-4 h-4" aria-hidden="true" />
            Open Settings
          </button>
        </>
      )}

      {recorder.phase === 'error' && (
        <>
          <p className="text-heading-sm font-semibold text-text-primary mb-1.5">Recording failed</p>
          <p className="text-sm text-text-secondary mb-6 max-w-xs">{recorder.errorMessage}</p>
          <button
            type="button"
            onClick={onStart}
            className="inline-flex items-center gap-2 rounded-xl bg-brand px-5 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            Try Again
          </button>
        </>
      )}

      {recorder.phase === 'recording' && (
        <>
          <div className="w-20 h-20 rounded-2xl flex items-center justify-center border border-red-500/30 bg-red-500/10 mb-6 animate-pulse">
            <Mic className="w-9 h-9 text-red-500" aria-hidden="true" />
          </div>
          <p className="text-3xl font-mono font-semibold text-text-primary mb-6 tabular-nums">
            {formatDuration(recorder.durationMs)}
          </p>
          <button
            type="button"
            onClick={onStop}
            className="inline-flex items-center gap-2 rounded-xl bg-red-500 px-5 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            <Square className="w-4 h-4" aria-hidden="true" />
            Stop Recording
          </button>
        </>
      )}

      {recorder.phase === 'stopped' && recorder.file && (
        <>
          <div className="w-20 h-20 rounded-2xl flex items-center justify-center border border-chrome/8 bg-chrome/[0.04] mb-6">
            <Mic className="w-9 h-9 text-brand" aria-hidden="true" />
          </div>
          <p className="text-heading-sm font-semibold text-text-primary mb-1.5">
            Recording ready — {formatDuration(recorder.durationMs)}
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 mt-5">
            <button
              type="button"
              onClick={toggle}
              className={cn(
                'inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors',
                'border border-chrome/10 bg-chrome/[0.03] text-text-primary hover:bg-chrome/[0.06]'
              )}
            >
              {player.isPlaying ? <Pause className="w-4 h-4" aria-hidden="true" /> : <Play className="w-4 h-4" aria-hidden="true" />}
              {player.isPlaying ? 'Pause' : 'Play'}
            </button>
            <button
              type="button"
              onClick={onReRecord}
              className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium border border-chrome/10 bg-chrome/[0.03] text-text-primary hover:bg-chrome/[0.06] transition-colors"
            >
              <RotateCcw className="w-4 h-4" aria-hidden="true" />
              Re-record
            </button>
            <button
              type="button"
              onClick={() => recorder.file && onAnalyze(recorder.file)}
              className="inline-flex items-center gap-2 rounded-xl bg-brand px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
            >
              <Sparkles className="w-4 h-4" aria-hidden="true" />
              Analyze Recording
            </button>
          </div>
        </>
      )}
    </motion.div>
  )
}
