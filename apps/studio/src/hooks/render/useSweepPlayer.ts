/**
 * useSweepPlayer — render a cartridge's parameter sweep on the server and play
 * its frames in the viewer.
 *
 * Lives in ProjectProvider, not in the panel that starts it: the sidebar's
 * Design tab unmounts when another tab is chosen, and on a phone the whole
 * sidebar is a sheet the visitor closes to watch. Playback must survive both,
 * so the state (and the stream, and the timers) belong above them.
 *
 * Frames come from `POST /api/projects/<slug>/animations/<id>/render`, an SSE
 * stream of `frame_done` progress events and one `complete` event carrying
 * every frame's part URLs. The endpoint answers 403 to a tier without the
 * `animation` feature; that is reported as `forbidden` so the caller can offer
 * the upgrade instead of showing a failure.
 *
 * With `prefers-reduced-motion: reduce` nothing plays on its own: the frames
 * arrive paused on the first one, and Play runs one pass and stops, no loop.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { apiFetch } from '../../services/core/apiClient'
import { getApiBase } from '../../services/core/backendDetection'
import { sweepFrameInterval, type SweepDefinition } from '../../lib/sweeps'

export interface SweepFramePart {
  /** The manifest part id, used for the part's colour. */
  part: string
  url: string
}

export interface SweepFrame {
  frame_index: number
  parts: SweepFramePart[]
}

export type SweepStatus = 'idle' | 'rendering' | 'playing' | 'paused' | 'error'

/** What went wrong, for the caller to put into words. */
export type SweepErrorCode = 'render_failed' | 'no_canvas'

export interface SweepError {
  code: SweepErrorCode
  /** The server's own message, when it sent one. */
  detail?: string
}

/** How a `play()` call ended. */
export type SweepPlayResult = 'ready' | 'forbidden' | 'error' | 'cancelled' | 'busy'

export interface SweepPlayer {
  status: SweepStatus
  /** The sweep being rendered or shown. */
  sweep: SweepDefinition | null
  /** Render progress, 0–100. */
  progress: number
  frames: SweepFrame[]
  /** The frame on screen. */
  index: number
  error: SweepError | null
  /** A WebM recording is running. */
  exporting: boolean
  /** Whether playback loops (false under reduced motion). */
  loops: boolean
  play: (sweep: SweepDefinition) => Promise<SweepPlayResult>
  cancel: () => void
  pause: () => void
  resume: () => void
  seek: (index: number) => void
  /** Leave the sweep and show the configuration again. */
  stop: () => void
  exportWebM: () => void
}

interface SSEEvent {
  event: string
  progress?: number
  frames?: Array<{ frame_index?: number; parts?: Array<{ part?: string; url?: string }> }>
  error?: string
}

class SweepRenderError extends Error {
  constructor(public detail: string) {
    super(detail)
    this.name = 'SweepRenderError'
  }
}

/** Parse an SSE stream and call onEvent for each `data:` line. */
async function consumeSSE(response: Response, onEvent: (event: SSEEvent) => void, signal: AbortSignal) {
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    if (signal.aborted) break
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      // The try covers the parse only, so an error the handler raises (an
      // `error` event) reaches the caller instead of being read as a
      // malformed line.
      let event: SSEEvent
      try {
        event = JSON.parse(line.slice(6)) as SSEEvent
      } catch {
        continue
      }
      onEvent(event)
    }
  }
}

/** Frames as the viewer needs them: every part with a URL, in frame order. */
function normaliseFrames(raw: SSEEvent['frames']): SweepFrame[] {
  return (raw ?? []).map((frame, i) => ({
    frame_index: typeof frame.frame_index === 'number' ? frame.frame_index : i,
    parts: (frame.parts ?? [])
      .filter((p): p is { part?: string; url: string } => typeof p.url === 'string' && p.url !== '')
      .map((p, j) => ({ part: typeof p.part === 'string' && p.part ? p.part : `part-${j}`, url: p.url })),
  })).filter(frame => frame.parts.length > 0)
}

function prefersReducedMotion(): boolean {
  try {
    return typeof window !== 'undefined'
      && typeof window.matchMedia === 'function'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches === true
  } catch {
    return false
  }
}

/** The 3D viewer's canvas, the one a recording captures. */
function viewerCanvas(): HTMLCanvasElement | null {
  if (typeof document === 'undefined') return null
  return document.querySelector<HTMLCanvasElement>('[data-testid="viewer-root"] canvas')
    ?? document.querySelector<HTMLCanvasElement>('canvas')
}

export function useSweepPlayer(projectSlug: string | null | undefined): SweepPlayer {
  const [status, setStatus] = useState<SweepStatus>('idle')
  const [sweep, setSweep] = useState<SweepDefinition | null>(null)
  const [progress, setProgress] = useState(0)
  const [frames, setFrames] = useState<SweepFrame[]>([])
  const [index, setIndex] = useState(0)
  const [error, setError] = useState<SweepError | null>(null)
  const [exporting, setExporting] = useState(false)
  const [loops] = useState(() => !prefersReducedMotion())

  const abortRef = useRef<AbortController | null>(null)
  const exportTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  // The export's recorder and the canvas stream it records, so leaving or
  // stopping mid-export can end both instead of recording for the life of the tab.
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const discardRef = useRef(false)
  // The interval reads the frame on screen from here, so advancing never has
  // to set state from inside another state update.
  const indexRef = useRef(0)
  const framesRef = useRef<SweepFrame[]>([])

  const showFrame = useCallback((next: number) => {
    indexRef.current = next
    setIndex(next)
  }, [])

  const clearExportTimer = useCallback(() => {
    if (exportTimerRef.current) clearInterval(exportTimerRef.current)
    exportTimerRef.current = null
  }, [])

  const releaseStream = useCallback(() => {
    streamRef.current?.getTracks().forEach(track => track.stop())
    streamRef.current = null
  }, [])

  // Abandon an export in progress: no download, and the recorder and its
  // stream are ended rather than left buffering in the background.
  const clearExport = useCallback(() => {
    clearExportTimer()
    const recorder = recorderRef.current
    recorderRef.current = null
    if (recorder && recorder.state !== 'inactive') {
      discardRef.current = true
      recorder.stop()
    }
    releaseStream()
  }, [clearExportTimer, releaseStream])

  const play = useCallback(async (next: SweepDefinition): Promise<SweepPlayResult> => {
    if (!projectSlug) return 'error'
    if (abortRef.current) return 'busy'
    clearExport()
    setExporting(false)
    const controller = new AbortController()
    abortRef.current = controller
    setSweep(next)
    setStatus('rendering')
    setProgress(0)
    setError(null)
    framesRef.current = []
    setFrames([])
    showFrame(0)

    try {
      const res = await apiFetch(
        `${getApiBase()}/api/projects/${encodeURIComponent(projectSlug)}/animations/${encodeURIComponent(next.id)}/render`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ parameters: {} }),
          signal: controller.signal,
        },
      )
      if (res.status === 403) {
        setStatus('idle')
        setSweep(null)
        return 'forbidden'
      }
      if (!res.ok) {
        let detail = `HTTP ${res.status}`
        try {
          const body = await res.json()
          if (body && typeof body.error === 'string') detail = body.error
        } catch { /* a body that is not JSON keeps the status line */ }
        throw new SweepRenderError(detail)
      }

      let received: SweepFrame[] = []
      await consumeSSE(res, event => {
        if (event.event === 'frame_done') {
          setProgress(typeof event.progress === 'number' ? event.progress : 0)
        } else if (event.event === 'complete') {
          received = normaliseFrames(event.frames)
        } else if (event.event === 'error') {
          throw new SweepRenderError(event.error ?? '')
        }
      }, controller.signal)

      if (controller.signal.aborted) return 'cancelled'
      if (received.length === 0) throw new SweepRenderError('')
      framesRef.current = received
      setFrames(received)
      setProgress(100)
      showFrame(0)
      setStatus(loops && received.length > 1 ? 'playing' : 'paused')
      return 'ready'
    } catch (err) {
      if (controller.signal.aborted || (err instanceof Error && err.name === 'AbortError')) {
        return 'cancelled'
      }
      setError({ code: 'render_failed', detail: err instanceof SweepRenderError ? err.detail || undefined : undefined })
      setStatus('error')
      return 'error'
    } finally {
      if (abortRef.current === controller) abortRef.current = null
    }
  }, [projectSlug, loops, showFrame, clearExport])

  const stop = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    clearExport()
    setExporting(false)
    framesRef.current = []
    setFrames([])
    showFrame(0)
    setProgress(0)
    setError(null)
    setSweep(null)
    setStatus('idle')
  }, [showFrame, clearExport])

  // Cancelling a render is leaving it: nothing was played yet.
  const cancel = stop

  // While an export steps through the frames, the controls wait: a second
  // driver of the frame on screen would garble the recording.
  const pause = useCallback(() => {
    if (exportTimerRef.current) return
    setStatus(current => (current === 'playing' ? 'paused' : current))
  }, [])

  const resume = useCallback(() => {
    if (exportTimerRef.current || framesRef.current.length < 2) return
    // One pass under reduced motion starts again from the first frame.
    if (indexRef.current >= framesRef.current.length - 1) showFrame(0)
    setStatus(current => (current === 'paused' ? 'playing' : current))
  }, [showFrame])

  const seek = useCallback((next: number) => {
    const count = framesRef.current.length
    if (exportTimerRef.current || count === 0) return
    const clamped = Math.min(Math.max(0, Math.round(next)), count - 1)
    // Choosing a frame is taking control of the sweep.
    setStatus(current => (current === 'playing' ? 'paused' : current))
    showFrame(clamped)
  }, [showFrame])

  // Playback: hold each frame for duration / frames, then loop or stop.
  useEffect(() => {
    if (status !== 'playing' || frames.length < 2) return
    const timer = setInterval(() => {
      const next = indexRef.current + 1
      if (next < frames.length) {
        showFrame(next)
      } else if (loops) {
        showFrame(0)
      } else {
        setStatus('paused')
      }
    }, sweepFrameInterval(sweep, frames.length))
    return () => clearInterval(timer)
  }, [status, frames, sweep, loops, showFrame])

  const exportWebM = useCallback(() => {
    const list = framesRef.current
    if (list.length === 0 || exporting) return
    const canvas = viewerCanvas()
    if (!canvas || typeof canvas.captureStream !== 'function' || typeof MediaRecorder === 'undefined') {
      setError({ code: 'no_canvas' })
      return
    }
    setError(null)
    const wasPlaying = status === 'playing'
    setStatus('paused')
    setExporting(true)

    const stream = canvas.captureStream(30)
    streamRef.current = stream
    discardRef.current = false
    const recorder = new MediaRecorder(stream, {
      mimeType: MediaRecorder.isTypeSupported('video/webm;codecs=vp9') ? 'video/webm;codecs=vp9' : 'video/webm',
    })
    const chunks: Blob[] = []
    recorder.ondataavailable = (e: BlobEvent) => {
      if (e.data.size > 0) chunks.push(e.data)
    }
    recorder.onstop = () => {
      stream.getTracks().forEach(track => track.stop())
      if (streamRef.current === stream) streamRef.current = null
      if (recorderRef.current === recorder) recorderRef.current = null
      // Abandoned (Stop, a new sweep, leaving the cartridge): nothing to save.
      if (discardRef.current) {
        discardRef.current = false
        return
      }
      const blob = new Blob(chunks, { type: 'video/webm' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${projectSlug ?? 'cartridge'}-sweep-${sweep?.id ?? 'frames'}.webm`
      a.click()
      // Revoking in the same task can cancel the download in some browsers.
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      setExporting(false)
      setStatus(current => (current === 'paused' && wasPlaying ? 'playing' : current))
    }
    recorderRef.current = recorder
    recorder.start()

    // Step through every frame once, then stop the recorder.
    let frameIdx = 0
    showFrame(0)
    clearExportTimer()
    exportTimerRef.current = setInterval(() => {
      frameIdx += 1
      if (frameIdx >= list.length) {
        clearExportTimer()
        recorder.stop()
        return
      }
      showFrame(frameIdx)
    }, sweepFrameInterval(sweep, list.length))
  }, [exporting, status, projectSlug, sweep, showFrame, clearExportTimer])

  // Leaving the cartridge abandons the stream (the server cancels its queued
  // frame parts when the client goes away) and the timers.
  useEffect(() => () => {
    abortRef.current?.abort()
    clearExport()
  }, [clearExport])

  return {
    status, sweep, progress, frames, index, error, exporting, loops,
    play, cancel, pause, resume, seek, stop, exportWebM,
  }
}
