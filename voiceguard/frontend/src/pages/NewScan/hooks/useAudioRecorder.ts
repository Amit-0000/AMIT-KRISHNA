import { useCallback, useEffect, useRef, useState } from 'react'
import { VoiceRecorder } from '@independo/capacitor-voice-recorder'
import { NativeSettings, AndroidSettings } from 'capacitor-native-settings'

export type RecorderPhase =
  | 'idle'
  | 'requesting-permission'
  | 'permission-denied'
  | 'permission-denied-permanently'
  | 'recording'
  | 'stopped'
  | 'error'

export interface RecorderState {
  phase: RecorderPhase
  durationMs: number
  file: File | null
  objectUrl: string | null
  errorMessage: string | null
}

const initial: RecorderState = {
  phase: 'idle',
  durationMs: 0,
  file: null,
  objectUrl: null,
  errorMessage: null,
}

function base64ToFile(base64: string, mimeType: string, extension: string): File {
  const bytes = atob(base64)
  const buffer = new Uint8Array(bytes.length)
  for (let i = 0; i < bytes.length; i++) buffer[i] = bytes.charCodeAt(i)
  return new File([buffer], `recording-${Date.now()}.${extension}`, { type: mimeType })
}

// Real device microphone recording via the native Android MediaRecorder
// (through @independo/capacitor-voice-recorder), not WebView getUserMedia —
// Android's WebView doesn't forward getUserMedia's permission prompt to the
// OS by default, and a native plugin gives a real recorded file with none of
// that plumbing to build ourselves. On Android this plugin hardcodes raw
// AAC/ADTS output (mimeType audio/aac, extension .aac — not an .m4a/MP4
// container, confirmed via a real device recording), which
// api/core/audio_formats.ALLOWED_AUDIO_EXTENSIONS accepts.
export function useAudioRecorder() {
  const [state, setState] = useState<RecorderState>(initial)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startedAtRef = useRef<number>(0)
  const deniedOnceRef = useRef(false)

  const stopTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  useEffect(() => stopTimer, [stopTimer])

  const startRecording = useCallback(async () => {
    setState((s) => ({ ...s, phase: 'requesting-permission', errorMessage: null }))
    try {
      const hasPermission = await VoiceRecorder.hasAudioRecordingPermission().catch(() => ({ value: false }))
      if (!hasPermission.value) {
        const requested = await VoiceRecorder.requestAudioRecordingPermission()
        if (!requested.value) {
          setState((s) => ({
            ...s,
            phase: deniedOnceRef.current ? 'permission-denied-permanently' : 'permission-denied',
          }))
          deniedOnceRef.current = true
          return
        }
      }

      await VoiceRecorder.startRecording()
      startedAtRef.current = Date.now()
      setState({ ...initial, phase: 'recording', durationMs: 0 })
      timerRef.current = setInterval(() => {
        setState((s) => (s.phase === 'recording' ? { ...s, durationMs: Date.now() - startedAtRef.current } : s))
      }, 250)
    } catch (err) {
      setState((s) => ({
        ...s,
        phase: 'error',
        errorMessage: err instanceof Error ? err.message : 'Could not start recording.',
      }))
    }
  }, [])

  const stopRecording = useCallback(async () => {
    stopTimer()
    try {
      const result = await VoiceRecorder.stopRecording()
      const { recordDataBase64, mimeType, fileExtension } = result.value
      const file = base64ToFile(recordDataBase64, mimeType, fileExtension)
      const objectUrl = URL.createObjectURL(file)
      setState((s) => ({ ...s, phase: 'stopped', file, objectUrl, durationMs: s.durationMs }))
    } catch (err) {
      setState((s) => ({
        ...s,
        phase: 'error',
        errorMessage: err instanceof Error ? err.message : 'Recording failed — please try again.',
      }))
    }
  }, [stopTimer])

  const reRecord = useCallback(() => {
    setState((s) => {
      if (s.objectUrl) URL.revokeObjectURL(s.objectUrl)
      return initial
    })
  }, [])

  const reset = useCallback(() => {
    stopTimer()
    setState((s) => {
      if (s.objectUrl) URL.revokeObjectURL(s.objectUrl)
      return initial
    })
  }, [stopTimer])

  const openAppSettings = useCallback(() => {
    void NativeSettings.openAndroid({ option: AndroidSettings.ApplicationDetails })
  }, [])

  return { state, startRecording, stopRecording, reRecord, reset, openAppSettings }
}
