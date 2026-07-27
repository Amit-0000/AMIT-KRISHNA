import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'

interface WaveformVisualizerProps {
  objectUrl: string | null
  currentTime: number
  duration: number
  onSeek: (fraction: number) => void
  isPlaying: boolean
}

const NUM_BARS = 280

export function WaveformVisualizer({
  objectUrl,
  currentTime,
  duration,
  onSeek,
  isPlaying,
}: WaveformVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [amplitudes, setAmplitudes] = useState<Float32Array | null>(null)
  const [decoding, setDecoding] = useState(false)

  // Decode audio to amplitude bars
  useEffect(() => {
    if (!objectUrl) {
      setAmplitudes(null)
      return
    }

    let cancelled = false
    setDecoding(true)
    setAmplitudes(null)

    const decode = async () => {
      try {
        const AudioCtx =
          window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof AudioContext })
            .webkitAudioContext

        const ctx = new AudioCtx()
        const response = await fetch(objectUrl)
        const buffer = await response.arrayBuffer()
        const audioBuffer = await ctx.decodeAudioData(buffer)
        await ctx.close()

        if (cancelled) return

        const channelData = audioBuffer.getChannelData(0)
        const blockSize = Math.floor(channelData.length / NUM_BARS)
        const bars = new Float32Array(NUM_BARS)

        for (let i = 0; i < NUM_BARS; i++) {
          let sum = 0
          for (let j = 0; j < blockSize; j++) {
            sum += Math.abs(channelData[i * blockSize + j] ?? 0)
          }
          bars[i] = sum / blockSize
        }

        // Normalize to [0, 1]
        let max = 0
        for (let i = 0; i < bars.length; i++) {
          if (bars[i] > max) max = bars[i]
        }
        if (max > 0) {
          for (let i = 0; i < bars.length; i++) bars[i] /= max
        }

        setAmplitudes(bars)
      } catch {
        setAmplitudes(null)
      } finally {
        if (!cancelled) setDecoding(false)
      }
    }

    decode()
    return () => { cancelled = true }
  }, [objectUrl])

  // Redraw canvas when amplitudes or playhead changes
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !amplitudes) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const w = canvas.offsetWidth
    const h = canvas.offsetHeight
    canvas.width = w * dpr
    canvas.height = h * dpr
    ctx.scale(dpr, dpr)
    ctx.clearRect(0, 0, w, h)

    const barW = w / NUM_BARS
    const progress = duration > 0 ? currentTime / duration : 0

    for (let i = 0; i < NUM_BARS; i++) {
      const amp = amplitudes[i] ?? 0
      const barH = Math.max(2, amp * h * 0.88)
      const x = i * barW
      const y = (h - barH) / 2
      const fraction = i / NUM_BARS

      ctx.fillStyle = fraction <= progress ? '#7B6CEA' : 'rgba(255,255,255,0.10)'

      ctx.beginPath()
      ctx.roundRect(x + barW * 0.12, y, barW * 0.76, barH, 1.5)
      ctx.fill()
    }
  }, [amplitudes, currentTime, duration])

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    onSeek(Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)))
  }

  const handleCanvasKeyDown = (e: React.KeyboardEvent<HTMLCanvasElement>) => {
    const step = 0.05
    const cur = duration > 0 ? currentTime / duration : 0
    if (e.key === 'ArrowRight') { e.preventDefault(); onSeek(Math.min(1, cur + step)) }
    if (e.key === 'ArrowLeft')  { e.preventDefault(); onSeek(Math.max(0, cur - step)) }
    if (e.key === 'Home')       { e.preventDefault(); onSeek(0) }
    if (e.key === 'End')        { e.preventDefault(); onSeek(1) }
  }

  // Decoding spinner
  if (decoding) {
    return (
      <div className="w-full h-14 flex items-center justify-center" aria-label="Decoding audio…">
        <div className="flex items-end gap-1">
          {Array.from({ length: 5 }).map((_, i) => (
            <motion.div
              key={i}
              className="w-1 bg-brand/40 rounded-full"
              animate={{ height: ['6px', '22px', '6px'] }}
              transition={{
                duration: 0.8,
                repeat: Infinity,
                delay: i * 0.1,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
      </div>
    )
  }

  // No waveform data — animated placeholder bars
  if (!amplitudes) {
    return (
      <div
        className="w-full h-14 flex items-end justify-center gap-px overflow-hidden"
        aria-hidden="true"
      >
        {Array.from({ length: 56 }).map((_, i) => {
          const baseH = 20 + Math.sin(i * 0.45) * 12 + Math.cos(i * 0.3) * 8
          return (
            <motion.div
              key={i}
              className="flex-1 rounded-sm"
              style={{
                background: i % 5 === 0 ? 'rgba(123,108,234,0.25)' : 'rgba(255,255,255,0.08)',
              }}
              animate={
                isPlaying
                  ? {
                      height: [
                        `${baseH * 0.4}px`,
                        `${baseH}px`,
                        `${baseH * 0.3}px`,
                      ],
                    }
                  : { height: `${baseH * 0.5}px` }
              }
              transition={
                isPlaying
                  ? {
                      duration: 0.5 + (i % 4) * 0.15,
                      repeat: Infinity,
                      delay: (i * 0.04) % 0.8,
                      ease: 'easeInOut',
                    }
                  : { duration: 0.3 }
              }
            />
          )
        })}
      </div>
    )
  }

  // Real waveform canvas
  return (
    <canvas
      ref={canvasRef}
      className="w-full h-14 cursor-pointer rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
      onClick={handleCanvasClick}
      onKeyDown={handleCanvasKeyDown}
      tabIndex={0}
      role="slider"
      aria-label="Audio seek — click or use arrow keys"
      aria-valuenow={Math.round(currentTime)}
      aria-valuemin={0}
      aria-valuemax={Math.round(duration)}
    />
  )
}
