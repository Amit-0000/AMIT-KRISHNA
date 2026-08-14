import { motion } from 'framer-motion'
import { FileAudio, X, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { AudioMetadata } from '../types'

interface FileCardProps {
  metadata: AudioMetadata
  onRemove: () => void
  replaceInputId: string
  onBrowse: (e: React.ChangeEvent<HTMLInputElement>) => void
}

function fmtSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function fmtDuration(seconds: number | null): string {
  if (seconds === null) return ''
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function audioFormat(mime: string, name: string): string {
  const map: Record<string, string> = {
    'audio/mpeg': 'MP3',
    'audio/mp3': 'MP3',
    'audio/wav': 'WAV',
    'audio/x-wav': 'WAV',
    'audio/ogg': 'OGG',
    'audio/flac': 'FLAC',
    'audio/x-flac': 'FLAC',
    'audio/aiff': 'AIFF',
    'audio/x-aiff': 'AIFF',
    'audio/mp4': 'M4A',
    'audio/m4a': 'M4A',
    'audio/x-m4a': 'M4A',
    'video/mp4': 'M4A',
  }
  return map[mime] ?? name.split('.').pop()?.toUpperCase() ?? 'AUDIO'
}

export function FileCard({ metadata, onRemove, replaceInputId, onBrowse }: FileCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.99 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.3, ease: [0.25, 0, 0, 1] }}
      className="card-base rounded-xl p-4 flex items-start gap-4"
    >
      {/* File icon */}
      <div className="w-12 h-12 rounded-xl bg-brand-muted border border-brand-border flex items-center justify-center flex-shrink-0">
        <FileAudio className="w-5 h-5 text-brand" aria-hidden="true" />
      </div>

      {/* Metadata */}
      <div className="flex-1 min-w-0">
        <p
          className="text-sm font-semibold text-text-primary truncate"
          title={metadata.name}
        >
          {metadata.name}
        </p>
        <div className="flex flex-wrap items-center gap-2 mt-1.5">
          <Badge variant="neutral" className="text-[11px] px-2 py-0.5">
            {audioFormat(metadata.type, metadata.name)}
          </Badge>
          <span className="text-xs text-text-tertiary">{fmtSize(metadata.size)}</span>
          {metadata.duration !== null && metadata.duration > 0 && (
            <span className="text-xs text-text-tertiary">
              {fmtDuration(metadata.duration)}
            </span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1.5 flex-shrink-0">
        {/* Replace */}
        <label
          htmlFor={replaceInputId}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-chrome/5 border border-transparent hover:border-chrome/8 transition-colors cursor-pointer focus-within:ring-2 focus-within:ring-brand"
          title="Replace file"
        >
          <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
          Replace
          <input
            id={replaceInputId}
            type="file"
            accept="audio/*,.wav,.mp3,.ogg,.flac,.aiff,.aif,.m4a"
            className="sr-only"
            onChange={onBrowse}
            tabIndex={-1}
            aria-label="Replace audio file"
          />
        </label>

        {/* Remove */}
        <button
          onClick={onRemove}
          className="w-7 h-7 rounded-lg flex items-center justify-center text-text-tertiary hover:text-ai hover:bg-ai-muted transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          aria-label="Remove file"
        >
          <X className="w-3.5 h-3.5" aria-hidden="true" />
        </button>
      </div>
    </motion.div>
  )
}
