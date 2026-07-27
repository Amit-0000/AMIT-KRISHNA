import { useCallback, useEffect, useReducer, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import type { UploadState, ValidationError } from '../types'
import { submitScan } from '../services/uploadApi'

// ─── Constants ────────────────────────────────────────────────────────────────

const ACCEPTED_MIME: Record<string, string> = {
  'audio/wav': 'WAV',
  'audio/x-wav': 'WAV',
  'audio/mpeg': 'MP3',
  'audio/mp3': 'MP3',
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
const ACCEPTED_EXT = /\.(wav|mp3|ogg|flac|aiff|aif|m4a)$/i
const MAX_SIZE = 50 * 1024 * 1024    // 50 MB
const MAX_DURATION = 600              // 10 minutes

// ─── State machine ────────────────────────────────────────────────────────────

type Action =
  | { type: 'VALIDATING' }
  | { type: 'SET_FILE'; file: File; objectUrl: string; duration: number | null }
  | { type: 'VALIDATION_ERRORS'; errors: ValidationError[] }
  | { type: 'START_UPLOAD' }
  | { type: 'SET_PROGRESS'; progress: number }
  | { type: 'UPLOAD_SUCCESS'; scanId: string }
  | { type: 'UPLOAD_ERROR'; message: string }
  | { type: 'CLEAR' }

const initial: UploadState = {
  phase: 'idle',
  file: null,
  metadata: null,
  validation: null,
  progress: 0,
  scanId: null,
  errorMessage: null,
  objectUrl: null,
}

function reducer(state: UploadState, action: Action): UploadState {
  switch (action.type) {
    case 'VALIDATING':
      return { ...initial, phase: 'validating' }

    case 'SET_FILE': {
      const f = action.file
      return {
        ...state,
        phase: 'ready',
        file: f,
        metadata: {
          name: f.name,
          size: f.size,
          type: f.type,
          duration: action.duration,
          lastModified: f.lastModified,
        },
        validation: { valid: true, errors: [] },
        progress: 0,
        scanId: null,
        errorMessage: null,
        objectUrl: action.objectUrl,
      }
    }

    case 'VALIDATION_ERRORS':
      return {
        ...initial,
        phase: 'error',
        validation: { valid: false, errors: action.errors },
      }

    case 'START_UPLOAD':
      return { ...state, phase: 'uploading', progress: 0, errorMessage: null }

    case 'SET_PROGRESS':
      return { ...state, progress: action.progress }

    case 'UPLOAD_SUCCESS':
      return { ...state, phase: 'submitted', scanId: action.scanId }

    case 'UPLOAD_ERROR':
      return { ...state, phase: 'error', errorMessage: action.message, progress: 0 }

    case 'CLEAR':
      return { ...initial }

    default:
      return state
  }
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useFileUpload() {
  const [state, dispatch] = useReducer(reducer, initial)
  const navigate = useNavigate()
  const abortRef = useRef<AbortController | null>(null)
  const prevObjectUrl = useRef<string | null>(null)

  // Revoke old object URL when a new one is set
  useEffect(() => {
    if (state.objectUrl && state.objectUrl !== prevObjectUrl.current) {
      if (prevObjectUrl.current) URL.revokeObjectURL(prevObjectUrl.current)
      prevObjectUrl.current = state.objectUrl
    }
  }, [state.objectUrl])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (prevObjectUrl.current) URL.revokeObjectURL(prevObjectUrl.current)
      abortRef.current?.abort()
    }
  }, [])

  const extractDuration = useCallback((file: File): Promise<number | null> => {
    return new Promise((resolve) => {
      const audio = new Audio()
      const url = URL.createObjectURL(file)
      audio.preload = 'metadata'
      audio.onloadedmetadata = () => {
        URL.revokeObjectURL(url)
        resolve(isFinite(audio.duration) ? audio.duration : null)
      }
      audio.onerror = () => {
        URL.revokeObjectURL(url)
        resolve(null)
      }
      audio.src = url
    })
  }, [])

  const processFile = useCallback(
    async (file: File) => {
      dispatch({ type: 'VALIDATING' })

      const errors: ValidationError[] = []

      if (!ACCEPTED_MIME[file.type] && !ACCEPTED_EXT.test(file.name)) {
        errors.push({
          code: 'type',
          message:
            'Unsupported format. Please upload WAV, MP3, OGG, FLAC, AIFF, or M4A.',
        })
      }

      if (file.size > MAX_SIZE) {
        errors.push({
          code: 'size',
          message: `File is ${(file.size / 1024 / 1024).toFixed(1)} MB — maximum is 50 MB.`,
        })
      }

      if (errors.length > 0) {
        dispatch({ type: 'VALIDATION_ERRORS', errors })
        return
      }

      const duration = await extractDuration(file)

      if (duration !== null && duration > MAX_DURATION) {
        dispatch({
          type: 'VALIDATION_ERRORS',
          errors: [
            {
              code: 'duration',
              message: `Audio is ${Math.round(duration / 60)} min long — maximum is 10 minutes.`,
            },
          ],
        })
        return
      }

      const objectUrl = URL.createObjectURL(file)
      dispatch({ type: 'SET_FILE', file, objectUrl, duration })
    },
    [extractDuration]
  )

  const handleDrop = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return
      processFile(files[0])
    },
    [processFile]
  )

  const handleBrowse = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      handleDrop(e.target.files)
      e.target.value = ''
    },
    [handleDrop]
  )

  const clearFile = useCallback(() => {
    abortRef.current?.abort()
    dispatch({ type: 'CLEAR' })
  }, [])

  const startUpload = useCallback(async () => {
    if (!state.file || state.phase === 'uploading') return

    dispatch({ type: 'START_UPLOAD' })
    abortRef.current = new AbortController()
    const signal = abortRef.current.signal

    try {
      const result = await submitScan(state.file, (pct) => {
        if (!signal.aborted) dispatch({ type: 'SET_PROGRESS', progress: pct })
      })

      if (signal.aborted) return

      dispatch({ type: 'UPLOAD_SUCCESS', scanId: result.scan_id })
      navigate(`/scan/processing?id=${result.scan_id}`)
    } catch (err: unknown) {
      if (signal.aborted) return

      let message = 'Upload failed. Please check your connection and try again.'

      if (err && typeof err === 'object' && 'response' in err) {
        const status = (err as { response?: { status?: number } }).response?.status
        if (status === 413) message = 'File is too large for the server. Try compressing or trimming the audio.'
        else if (status === 415) message = 'Audio format rejected by server. Try converting to WAV or MP3.'
        else if (status === 429) message = 'Daily scan limit reached. Please try again tomorrow.'
        else if (status === 503) message = 'Service temporarily unavailable. Please try again in a moment.'
      }

      dispatch({ type: 'UPLOAD_ERROR', message })
    }
  }, [state.file, state.phase, navigate])

  const cancelUpload = useCallback(() => {
    abortRef.current?.abort()
    dispatch({ type: 'CLEAR' })
  }, [])

  const retryValidation = useCallback(() => {
    dispatch({ type: 'CLEAR' })
  }, [])

  const retryUpload = useCallback(() => {
    if (state.file) {
      dispatch({ type: 'START_UPLOAD' })
      startUpload()
    }
  }, [state.file, startUpload])

  const acceptedFormats = Object.values(ACCEPTED_MIME).filter(
    (v, i, a) => a.indexOf(v) === i
  )

  return {
    state,
    handleDrop,
    handleBrowse,
    clearFile,
    startUpload,
    cancelUpload,
    retryValidation,
    retryUpload,
    acceptedFormats,
  }
}
