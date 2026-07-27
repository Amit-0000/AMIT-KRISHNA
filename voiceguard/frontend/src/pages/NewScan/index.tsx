import { useId } from 'react'
import { AnimatePresence } from 'framer-motion'
import { PageContainer } from '@/components/layout/PageContainer'
import { useFileUpload } from './hooks/useFileUpload'
import { useAudioPlayer } from './hooks/useAudioPlayer'
import { UploadDropzone } from './components/UploadDropzone'
import { FileCard } from './components/FileCard'
import { AudioPlayer } from './components/AudioPlayer'
import { UploadProgress } from './components/UploadProgress'
import { UploadValidation } from './components/UploadValidation'
import { PrivacyNotice } from './components/PrivacyNotice'
import { UploadActions } from './components/UploadActions'

export function NewScanPage() {
  const replaceInputId = useId()

  const {
    state,
    handleDrop,
    handleBrowse,
    clearFile,
    startUpload,
    cancelUpload,
    retryValidation,
    acceptedFormats,
  } = useFileUpload()

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
        {/* ── Dropzone ───────────────────────────────────────────── */}
        <AnimatePresence mode="wait">
          {showDropzone && (
            <UploadDropzone
              key="dropzone"
              onDrop={handleDrop}
              onBrowse={handleBrowse}
              acceptedFormats={acceptedFormats}
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
