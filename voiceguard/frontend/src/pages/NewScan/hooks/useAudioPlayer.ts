import { useCallback, useEffect, useRef, useState } from 'react'
import type { PlayerState } from '../types'

const DEFAULT: PlayerState = {
  isPlaying: false,
  currentTime: 0,
  duration: 0,
  volume: 1,
  isMuted: false,
}

export function useAudioPlayer(objectUrl: string | null) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [player, setPlayer] = useState<PlayerState>(DEFAULT)

  const patch = useCallback((partial: Partial<PlayerState>) => {
    setPlayer((prev) => ({ ...prev, ...partial }))
  }, [])

  useEffect(() => {
    if (!objectUrl) {
      audioRef.current?.pause()
      audioRef.current = null
      setPlayer(DEFAULT)
      return
    }

    const audio = new Audio(objectUrl)
    audioRef.current = audio

    audio.onloadedmetadata = () => patch({ duration: isFinite(audio.duration) ? audio.duration : 0 })
    audio.ontimeupdate = () => patch({ currentTime: audio.currentTime })
    audio.onended = () => patch({ isPlaying: false, currentTime: 0 })
    audio.onerror = () => patch({ isPlaying: false })
    audio.onvolumechange = () => patch({ volume: audio.volume, isMuted: audio.muted })

    return () => {
      audio.pause()
      audio.src = ''
      audioRef.current = null
    }
  }, [objectUrl, patch])

  const play = useCallback(() => {
    audioRef.current
      ?.play()
      .then(() => patch({ isPlaying: true }))
      .catch(() => {})
  }, [patch])

  const pause = useCallback(() => {
    audioRef.current?.pause()
    patch({ isPlaying: false })
  }, [patch])

  const toggle = useCallback(() => {
    if (audioRef.current?.paused === false) pause()
    else play()
  }, [play, pause])

  const seek = useCallback(
    (seconds: number) => {
      if (!audioRef.current) return
      audioRef.current.currentTime = Math.max(0, Math.min(seconds, audioRef.current.duration || 0))
      patch({ currentTime: audioRef.current.currentTime })
    },
    [patch]
  )

  const seekByFraction = useCallback(
    (fraction: number) => {
      if (!audioRef.current) return
      seek(fraction * (audioRef.current.duration || 0))
    },
    [seek]
  )

  const setVolume = useCallback(
    (vol: number) => {
      if (!audioRef.current) return
      audioRef.current.volume = Math.max(0, Math.min(1, vol))
      audioRef.current.muted = vol === 0
    },
    []
  )

  const toggleMute = useCallback(() => {
    if (!audioRef.current) return
    audioRef.current.muted = !audioRef.current.muted
  }, [])

  return { player, play, pause, toggle, seek, seekByFraction, setVolume, toggleMute }
}
