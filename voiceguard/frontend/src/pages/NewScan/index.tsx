import { useId, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { Upload as UploadIcon, Mic } from 'lucide-react'
import { cn } from '@/lib/utils'
import { isNativeApp } from '@/services/api'
import { PageContainer } from '@/components/layout/PageContainer'
import { useFileUpload } from './hooks/useFileUpload'
import { useAudioPlayer } from './hooks/useAudioPlayer'
import { useAudioRecorder } from './hooks/useAudioRecorder'
import { UploadDropzone } from './components/UploadDropzone'
import { RecordAudioPanel } from './components/RecordAudioPanel'
import { FileCard } from './components/FileCard'
import { AudioPlayer } from './components/AudioPlayer'
import { UploadProgress } from './components/UploadProgress'
import { UploadValidation } from './components/UploadValidation'
import { PrivacyNotice } from './components/PrivacyNotice'
import { UploadActions } from './components/UploadActions'

export function NewScanPage() {
  const replaceInputId = useId()
  // Recording is only offered inside the Android app — the web app has no
  // reliable way to forward getUserMedia's OS permission prompt, and this
  // isn't a feature the existing web UX asked for.
  const [mode, setMode] = useState<'upload' | 'record'>('upload')

  const {
    state,
    handleDrop,
    handleBrowse,
    handleRecordedFile,
    clearFile,
    startUpload,
    cancelUpload,
    retryValidation,
    acceptedFormats,
    maxSizeMb,
    maxDurationMinutes,
  } = useFileUpload()

  const recorder = useAudioRecorder()

  const { player, toggle, seekByFraction, setVolume, toggleMute, seek } =
    useAudioPlayer(state.objectUrl)

  // Derived state flags
  const isValidationError =
    state.phase === 'error' &&
    state.validation !== null &&
    !state.validation.valid &&
    state.validation.errors.length > 0

  const isUploadError =
    state.phase === 'error' && state.errorMessage !== null

  const hasFile =
    state.file !== null && (state.phase === 'ready' || state.phase === 'uploading' || isUploadError)

  const isUploading = state.phase === 'uploading'

  const showDropzone = !hasFile

  return (
    <PageContainer
      maxWidth="md"
      title="Analyze Audio"
      description="Upload an audio file to get a forensic-grade verdict — human or AI-generated."
    >
      <div className="space-y-4">
        {/* ── Upload / Record mode switch (Android app only) ───────── */}
        {isNativeApp && showDropzone && (
          <div className="inline-flex rounded-xl border border-chrome/10 bg-chrome/[0.02] p-1 mx-auto">
            <button
              type="button"
              onClick={() => setMode('upload')}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                mode === 'upload' ? 'bg-brand text-white' : 'text-text-secondary hover:text-text-primary'
              )}
            >
              <UploadIcon className="w-4 h-4" aria-hidden="true" />
              Upload Audio
            </button>
            <button
              type="button"
              onClick={() => setMode('record')}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                mode === 'record' ? 'bg-brand text-white' : 'text-text-secondary hover:text-text-primary'
              )}
            >
              <Mic className="w-4 h-4" aria-hidden="true" />
              Record Audio
            </button>
          </div>
        )}

        {/* ── Dropzone / Recorder ───────────────────────────────────── */}
        <AnimatePresence mode="wait">
          {showDropzone && (!isNativeApp || mode === 'upload') && (
            <UploadDropzone
              key="dropzone"
              onDrop={handleDrop}
              onBrowse={handleBrowse}
              acceptedFormats={acceptedFormats}
              maxSizeMb={maxSizeMb}
              maxDurationMinutes={maxDurationMinutes}
            />
          )}
          {showDropzone && isNativeApp && mode === 'record' && (
            <RecordAudioPanel
              key="recorder"
              recorder={recorder.state}
              onStart={recorder.startRecording}
              onStop={recorder.stopRecording}
              onReRecord={recorder.reRecord}
              onOpenSettings={recorder.openAppSettings}
              onAnalyze={(file) => {
                handleRecordedFile(file)
                recorder.reset()
                setMode('upload')
              }}
            />
          )}
        </AnimatePresence>

        {/* ── Validation errors ──────────────────────────────────── */}
        <AnimatePresence>
          {isValidationError && (
            <UploadValidation
              errors={state.validation!.errors}
              onDismiss={retryValidation}
            />
          )}
        </AnimatePresence>

        {/* ── File card + audio player ───────────────────────────── */}
        <AnimatePresence>
          {hasFile && state.metadata && (
            <>
              <FileCard
                key="file-card"
                metadata={state.metadata}
                onRemove={isUploading ? cancelUpload : clearFile}
                replaceInputId={replaceInputId}
                onBrowse={handleBrowse}
              />

              <AudioPlayer
                key="audio-player"
                objectUrl={state.objectUrl}
                player={player}
                onToggle={toggle}
                onSeekByFraction={seekByFraction}
                onSetVolume={setVolume}
                onToggleMute={toggleMute}
                onRestart={() => seek(0)}
              />
            </>
          )}
        </AnimatePresence>

        {/* ── Upload progress ─────────────────────────────────────── */}
        <AnimatePresence>
          {isUploading && <UploadProgress key="progress" progress={state.progress} />}
        </AnimatePresence>

        {/* ── CTA ─────────────────────────────────────────────────── */}
        <AnimatePresence>
          {hasFile && (
            <UploadActions
              key="actions"
              onAnalyze={startUpload}
              onCancel={isUploading ? cancelUpload : clearFile}
              isUploading={isUploading}
              errorMessage={isUploadError ? state.errorMessage : null}
            />
          )}
        </AnimatePresence>

        {/* ── Privacy notice — only when no file is loaded ─────────── */}
        <AnimatePresence>
          {!hasFile && !isValidationError && <PrivacyNotice key="privacy" />}
        </AnimatePresence>
      </div>
    </PageContainer>
  )
}
