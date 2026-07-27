export type UploadPhase =
  | 'idle'
  | 'validating'
  | 'ready'
  | 'uploading'
  | 'submitted'
  | 'error'

export type ValidationErrorCode = 'type' | 'size' | 'duration' | 'corrupt'

export interface ValidationError {
  code: ValidationErrorCode
  message: string
}

export interface FileValidation {
  valid: boolean
  errors: ValidationError[]
}

export interface AudioMetadata {
  name: string
  size: number
  type: string
  duration: number | null
  lastModified: number
}

export interface UploadState {
  phase: UploadPhase
  file: File | null
  metadata: AudioMetadata | null
  validation: FileValidation | null
  progress: number
  scanId: string | null
  errorMessage: string | null
  objectUrl: string | null
}

export interface PlayerState {
  isPlaying: boolean
  currentTime: number
  duration: number
  volume: number
  isMuted: boolean
}
