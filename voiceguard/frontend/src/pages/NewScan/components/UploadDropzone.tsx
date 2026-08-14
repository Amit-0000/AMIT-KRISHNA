import { useCallback, useId, useRef, useState, type DragEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, Music, FileAudio } from 'lucide-react'
import { cn } from '@/lib/utils'

interface UploadDropzoneProps {
  onDrop: (files: FileList | null) => void
  onBrowse: (e: React.ChangeEvent<HTMLInputElement>) => void
  acceptedFormats: string[]
  maxSizeMb: number
  maxDurationMinutes: number
  disabled?: boolean
}

export function UploadDropzone({
  onDrop,
  onBrowse,
  acceptedFormats,
  maxSizeMb,
  maxDurationMinutes,
  disabled = false,
}: UploadDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const dragCountRef = useRef(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const inputId = useId()

  const handleDragEnter = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    dragCountRef.current += 1
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    dragCountRef.current -= 1
    if (dragCountRef.current <= 0) {
      dragCountRef.current = 0
      setIsDragging(false)
    }
  }, [])

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    e.dataTransfer.dropEffect = 'copy'
  }, [])

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      dragCountRef.current = 0
      setIsDragging(false)
      if (!disabled) onDrop(e.dataTransfer.files)
    },
    [disabled, onDrop]
  )

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
      e.preventDefault()
      inputRef.current?.click()
    }
  }, [disabled])

  const handleClick = useCallback(() => {
    if (!disabled) inputRef.current?.click()
  }, [disabled])

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.4, ease: [0.25, 0, 0, 1] }}
    >
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="Upload audio file — drag and drop, or press Enter to browse"
        aria-disabled={disabled}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onKeyDown={handleKeyDown}
        onClick={handleClick}
        className={cn(
          'relative flex flex-col items-center justify-center',
          'min-h-[340px] rounded-2xl border-2 border-dashed',
          'transition-all duration-200 cursor-pointer select-none',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-bg-base',
          isDragging
            ? 'border-brand bg-brand-muted/20 scale-[1.005]'
            : 'border-chrome/10 bg-chrome/[0.02] hover:border-brand/40 hover:bg-brand-muted/8',
          disabled && 'cursor-not-allowed opacity-50 pointer-events-none'
        )}
      >
        {/* Drag glow overlay */}
        <AnimatePresence>
          {isDragging && (
            <motion.div
              className="absolute inset-0 rounded-2xl bg-brand/[0.04] pointer-events-none"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
            />
          )}
        </AnimatePresence>

        {/* Icon cluster */}
        <div className="relative mb-6">
          <motion.div
            animate={
              isDragging
                ? { scale: 1.08, y: -6 }
                : { scale: 1, y: 0 }
            }
            transition={{ duration: 0.25, ease: [0.25, 0, 0, 1] }}
            className={cn(
              'w-20 h-20 rounded-2xl flex items-center justify-center border transition-all duration-200',
              isDragging
                ? 'bg-brand-muted border-brand-border shadow-glow-brand'
                : 'bg-chrome/[0.04] border-chrome/8'
            )}
          >
            <Upload
              className={cn(
                'w-9 h-9 transition-colors duration-200',
                isDragging ? 'text-brand' : 'text-text-tertiary'
              )}
              aria-hidden="true"
            />
          </motion.div>

          {/* Decorative floating icons */}
          <div
            className="absolute -top-2 -right-7 w-8 h-8 rounded-xl bg-bg-elevated border border-chrome/6 flex items-center justify-center"
            aria-hidden="true"
          >
            <Music className="w-4 h-4 text-brand/50" />
          </div>
          <div
            className="absolute -bottom-2 -left-7 w-8 h-8 rounded-xl bg-bg-elevated border border-chrome/6 flex items-center justify-center"
            aria-hidden="true"
          >
            <FileAudio className="w-4 h-4 text-text-tertiary/60" />
          </div>
        </div>

        {/* Copy */}
        <div className="text-center px-8">
          <p className="text-heading-sm font-semibold text-text-primary mb-1.5">
            {isDragging ? 'Release to upload' : 'Drop your audio file here'}
          </p>
          <p className="text-sm text-text-secondary mb-5">
            or{' '}
            <label
              htmlFor={inputId}
              className="text-brand font-medium underline underline-offset-2 cursor-pointer hover:text-brand-light transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              browse files
            </label>
          </p>
          <p className="text-xs text-text-tertiary leading-relaxed">
            {acceptedFormats.join(' · ')}
            <span className="mx-2 text-text-tertiary/40">·</span>
            Up to {maxSizeMb} MB
            <span className="mx-2 text-text-tertiary/40">·</span>
            Max {maxDurationMinutes} minutes
          </p>
        </div>

        <input
          id={inputId}
          ref={inputRef}
          type="file"
          accept="audio/*,.wav,.mp3,.ogg,.flac,.aiff,.aif,.m4a"
          className="sr-only"
          onChange={onBrowse}
          aria-hidden="true"
          tabIndex={-1}
        />
      </div>
    </motion.div>
  )
}
