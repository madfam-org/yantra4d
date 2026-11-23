import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { axe } from '../../test/axe-setup'
import { toHaveNoViolations } from 'jest-axe'
import { LanguageProvider } from '../../contexts/system/LanguageProvider'
import { useSweepPlayer } from '../../hooks/render/useSweepPlayer'
import AnimationPanel from './AnimationPanel'

expect.extend(toHaveNoViolations)

// apiFetch calls the global fetch.
const mockFetch = vi.fn()
globalThis.fetch = mockFetch

const SWEEPS = [
  { id: 'grow', label: { en: 'Grow', es: 'Crecer' }, frames: 5, duration_ms: 2000, easing: 'ease-in-out', mode: 'default' },
  { id: 'reach', label: 'Reach', frames: 8, duration_ms: 2400, mode: 'arm' },
]

const FRAMES = [
  { frame_index: 0, parts: [{ part: 'body', url: '/static/f0_body.glb' }] },
  { frame_index: 1, parts: [{ part: 'body', url: '/static/f1_body.glb' }] },
]

/** A Response whose body streams the given SSE events. */
function sseResponse(events) {
  const encoder = new TextEncoder()
  let i = 0
  return {
    ok: true,
    status: 200,
    json: async () => ({}),
    body: {
      getReader: () => ({
        read: async () => {
          if (i >= events.length) return { done: true, value: undefined }
          const chunk = `data: ${JSON.stringify(events[i++])}\n\n`
          return { done: false, value: encoder.encode(chunk) }
        },
      }),
    },
  }
}

/** The real player hook behind the panel, with its state published for assertions. */
function Harness({ sweeps = SWEEPS, canPlay = true, onLocked = () => {}, currentMode = 'default', slug = 'test-project' }) {
  const player = useSweepPlayer(slug)
  return (
    <>
      <AnimationPanel
        sweeps={sweeps}
        player={player}
        canPlay={canPlay}
        onLocked={onLocked}
        labelOf={s => (typeof s.label === 'object' ? s.label.en : s.label)}
        currentMode={currentMode}
        modeLabelOf={id => (id === 'arm' ? 'Arm' : id)}
      />
      <output data-testid="probe" data-status={player.status} data-index={player.index} data-frames={player.frames.length} />
    </>
  )
}

function renderPanel(props = {}) {
  return render(
    <LanguageProvider defaultLanguage="en" storageKey="test-lang-sweep">
      <Harness {...props} />
    </LanguageProvider>,
  )
}

const probe = () => screen.getByTestId('probe')

async function playToFrames(events = [{ event: 'frame_done', progress: 50 }, { event: 'complete', frames: FRAMES }]) {
  mockFetch.mockResolvedValueOnce(sseResponse(events))
  fireEvent.click(screen.getByRole('button', { name: 'Play sweep Grow' }))
  await waitFor(() => expect(probe()).toHaveAttribute('data-frames', String(FRAMES.length)))
}

describe('AnimationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockReset()
    localStorage.removeItem('test-lang-sweep')
  })

  afterEach(() => {
    vi.useRealTimers()
    globalThis.__resetMediaQueries()
  })

  // --- What every visitor sees -------------------------------------------

  it('renders nothing when the cartridge declares no sweeps', () => {
    const { container } = renderPanel({ sweeps: [] })
    expect(container.querySelector('[data-testid="sweep-panel"]')).toBeNull()
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('lists every declared sweep with its frames and duration', () => {
    renderPanel()
    expect(screen.getByRole('heading', { name: 'Sweeps' })).toBeInTheDocument()
    expect(screen.getByText('Grow')).toBeInTheDocument()
    expect(screen.getByText('Reach')).toBeInTheDocument()
    expect(screen.getByText('5 frames · 2 s')).toBeInTheDocument()
    expect(screen.getByText('8 frames · 2.4 s')).toBeInTheDocument()
    // The list is read from the manifest: nothing is requested to show it.
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('says which mode a sweep shows when it is not the mode on screen', () => {
    renderPanel({ currentMode: 'default' })
    expect(screen.getByText('Shows the Arm mode')).toBeInTheDocument()
    expect(screen.queryByText('Shows the default mode')).not.toBeInTheDocument()
  })

  // --- Without playback in the tier ----------------------------------------

  it('without playback, offers the upgrade instead of a request that would be refused', () => {
    const onLocked = vi.fn()
    renderPanel({ canPlay: false, onLocked })

    expect(screen.getByText(/is a Pro feature/)).toBeInTheDocument()
    const locked = screen.getByRole('button', { name: 'Play sweep Grow: Pro feature' })
    expect(locked).toHaveAttribute('title', 'Pro tier required')
    expect(screen.queryByRole('button', { name: 'Play sweep Grow' })).not.toBeInTheDocument()

    fireEvent.click(locked)
    expect(onLocked).toHaveBeenCalledTimes(1)
    expect(mockFetch).not.toHaveBeenCalled()
    expect(probe()).toHaveAttribute('data-status', 'idle')
  })

  it('a refusal from the server (403) also offers the upgrade, not an error', async () => {
    const onLocked = vi.fn()
    renderPanel({ onLocked })
    mockFetch.mockResolvedValueOnce({ ok: false, status: 403, json: async () => ({ error: 'Animation rendering requires Pro tier or above.' }) })

    fireEvent.click(screen.getByRole('button', { name: 'Play sweep Grow' }))

    await waitFor(() => expect(onLocked).toHaveBeenCalledTimes(1))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(probe()).toHaveAttribute('data-status', 'idle')
  })

  // --- With playback ---------------------------------------------------------

  it('Play renders the frames on the server and then plays them', async () => {
    renderPanel()
    await playToFrames()

    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toBe('/api/projects/test-project/animations/grow/render')
    expect(init.method).toBe('POST')
    expect(probe()).toHaveAttribute('data-status', 'playing')
    expect(screen.getByText('Frame 1 of 2')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Pause' })).toBeInTheDocument()
  })

  it('shows render progress while the frames are rendered', async () => {
    renderPanel()
    // The stream reports one frame, then stalls: the panel sits in its rendering state.
    let release
    const stalled = new Promise(resolve => { release = resolve })
    let sent = false
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({}),
      body: {
        getReader: () => ({
          read: async () => {
            if (!sent) {
              sent = true
              return { done: false, value: new TextEncoder().encode(`data: ${JSON.stringify({ event: 'frame_done', progress: 40 })}\n\n`) }
            }
            await stalled
            return { done: true, value: undefined }
          },
        }),
      },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Play sweep Grow' }))

    const bar = await screen.findByRole('progressbar', { name: 'Rendering the frames of Grow' })
    await waitFor(() => expect(bar).toHaveAttribute('aria-valuenow', '40'))
    expect(screen.getByText('Rendering frames · 40%')).toBeInTheDocument()
    // Another sweep cannot start meanwhile.
    expect(screen.getByRole('button', { name: 'Play sweep Reach' })).toBeDisabled()
    release()
  })

  it('surfaces a non-OK render response as an error with the server message', async () => {
    renderPanel()
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({ error: 'Renderer exploded' }) })
    fireEvent.click(screen.getByRole('button', { name: 'Play sweep Grow' }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent("The sweep's frames could not be rendered.")
    expect(alert).toHaveTextContent('Renderer exploded')
    expect(probe()).toHaveAttribute('data-status', 'error')
  })

  it('surfaces an SSE error event as an error', async () => {
    renderPanel()
    mockFetch.mockResolvedValueOnce(sseResponse([{ event: 'error', error: 'frame 3 failed' }]))
    fireEvent.click(screen.getByRole('button', { name: 'Play sweep Grow' }))

    expect(await screen.findByText('frame 3 failed')).toBeInTheDocument()
    // Dismissing the error returns the row to its Play control.
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(screen.getByRole('button', { name: 'Play sweep Grow' })).toBeInTheDocument()
  })

  it('a stream that completes with no frames is an error, not an empty player', async () => {
    renderPanel()
    mockFetch.mockResolvedValueOnce(sseResponse([{ event: 'complete', frames: [] }]))
    fireEvent.click(screen.getByRole('button', { name: 'Play sweep Grow' }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('cancel during a render returns the panel to idle', async () => {
    renderPanel()
    // A render that never resolves leaves the panel in its rendering state.
    mockFetch.mockImplementationOnce(() => new Promise(() => { }))
    fireEvent.click(screen.getByRole('button', { name: 'Play sweep Grow' }))

    const cancel = await screen.findByRole('button', { name: /cancel/i })
    fireEvent.click(cancel)
    await waitFor(() => expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument())
    expect(probe()).toHaveAttribute('data-status', 'idle')
    expect(screen.getByRole('button', { name: 'Play sweep Grow' })).toBeEnabled()
  })

  it('playback advances through the frames and loops', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    renderPanel()
    await playToFrames()
    expect(probe()).toHaveAttribute('data-index', '0')

    // Each frame is held for duration / frames: 2000 ms / 2.
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(probe()).toHaveAttribute('data-index', '1')
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(probe()).toHaveAttribute('data-index', '0')
  })

  it('pause holds the frame; play continues from it', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    renderPanel()
    await playToFrames()

    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    expect(probe()).toHaveAttribute('data-status', 'paused')
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(probe()).toHaveAttribute('data-index', '0')

    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    expect(probe()).toHaveAttribute('data-status', 'playing')
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(probe()).toHaveAttribute('data-index', '1')
  })

  it('with reduced motion, frames arrive paused and Play runs one pass without looping', async () => {
    globalThis.__setMediaQuery('(prefers-reduced-motion: reduce)', true)
    vi.useFakeTimers({ shouldAdvanceTime: true })
    renderPanel()
    await playToFrames()

    expect(probe()).toHaveAttribute('data-status', 'paused')
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(probe()).toHaveAttribute('data-index', '0')

    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(probe()).toHaveAttribute('data-index', '1')
    // The last frame stops the pass instead of wrapping to the first.
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(probe()).toHaveAttribute('data-status', 'paused')
    expect(probe()).toHaveAttribute('data-index', '1')
  })

  it('choosing a frame on the scrubber shows it and pauses playback', async () => {
    renderPanel()
    await playToFrames()

    const scrubber = screen.getByRole('slider', { name: 'Frame of Grow' })
    fireEvent.keyDown(scrubber, { key: 'ArrowRight' })

    expect(probe()).toHaveAttribute('data-index', '1')
    expect(probe()).toHaveAttribute('data-status', 'paused')
    expect(screen.getByText('Frame 2 of 2')).toBeInTheDocument()
  })

  it('stop leaves the sweep and returns the row to its Play control', async () => {
    renderPanel()
    await playToFrames()

    fireEvent.click(screen.getByRole('button', { name: 'Stop and show my configuration' }))
    expect(probe()).toHaveAttribute('data-status', 'idle')
    expect(probe()).toHaveAttribute('data-frames', '0')
    expect(screen.queryByRole('slider')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Play sweep Grow' })).toBeInTheDocument()
  })

  it('a single-frame sweep shows its frame without play controls', async () => {
    renderPanel()
    mockFetch.mockResolvedValueOnce(sseResponse([{ event: 'complete', frames: [FRAMES[0]] }]))
    fireEvent.click(screen.getByRole('button', { name: 'Play sweep Grow' }))
    await waitFor(() => expect(probe()).toHaveAttribute('data-frames', '1'))

    expect(probe()).toHaveAttribute('data-status', 'paused')
    expect(screen.queryByRole('button', { name: 'Pause' })).not.toBeInTheDocument()
    expect(screen.queryByRole('slider')).not.toBeInTheDocument()
  })

  it('WebM export reports when there is no 3D view to record', async () => {
    renderPanel()
    await playToFrames()

    // jsdom renders no <canvas>: export must say so rather than throw.
    fireEvent.click(screen.getByRole('button', { name: /webm/i }))
    expect(await screen.findByText('There is no 3D view to record.')).toBeInTheDocument()
  })

  it('WebM export records the viewer canvas through every frame and downloads it', async () => {
    // jsdom has neither captureStream nor MediaRecorder; both are supplied
    // here so the export path can run end to end.
    const root = document.createElement('div')
    root.setAttribute('data-testid', 'viewer-root')
    const canvas = document.createElement('canvas')
    canvas.captureStream = vi.fn(() => ({ getTracks: () => [] }))
    root.appendChild(canvas)
    document.body.appendChild(root)

    const started = vi.fn()
    const stopped = vi.fn()
    class FakeRecorder {
      constructor() { this.ondataavailable = null; this.onstop = null }
      start() { started() }
      stop() {
        stopped()
        this.ondataavailable?.({ data: new Blob(['x']) })
        this.onstop?.()
      }
    }
    FakeRecorder.isTypeSupported = () => true
    globalThis.MediaRecorder = FakeRecorder
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => { })

    vi.useFakeTimers({ shouldAdvanceTime: true })
    renderPanel()
    await playToFrames()

    fireEvent.click(screen.getByRole('button', { name: /webm/i }))
    expect(started).toHaveBeenCalled()
    expect(canvas.captureStream).toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /recording/i })).toBeDisabled()

    // Past the last frame the recorder stops, which triggers the download.
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(stopped).toHaveBeenCalled()
    expect(clickSpy).toHaveBeenCalled()
    // Playback resumes as it was.
    expect(probe()).toHaveAttribute('data-status', 'playing')

    clickSpy.mockRestore()
    root.remove()
    delete globalThis.MediaRecorder
  })

  it('Stop during a WebM export ends the recorder and its stream, and downloads nothing', async () => {
    const root = document.createElement('div')
    root.setAttribute('data-testid', 'viewer-root')
    const canvas = document.createElement('canvas')
    const track = { stop: vi.fn() }
    canvas.captureStream = vi.fn(() => ({ getTracks: () => [track] }))
    root.appendChild(canvas)
    document.body.appendChild(root)

    const stopped = vi.fn()
    class FakeRecorder {
      constructor() { this.ondataavailable = null; this.onstop = null; this.state = 'inactive' }
      start() { this.state = 'recording' }
      stop() {
        stopped()
        this.state = 'inactive'
        this.ondataavailable?.({ data: new Blob(['x']) })
        this.onstop?.()
      }
    }
    FakeRecorder.isTypeSupported = () => true
    globalThis.MediaRecorder = FakeRecorder
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => { })

    vi.useFakeTimers({ shouldAdvanceTime: true })
    renderPanel()
    await playToFrames()

    fireEvent.click(screen.getByRole('button', { name: /webm/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Stop and show my configuration' }))

    expect(stopped).toHaveBeenCalledTimes(1)
    expect(track.stop).toHaveBeenCalled()
    // Nothing keeps stepping frames after Stop, and nothing is downloaded.
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(stopped).toHaveBeenCalledTimes(1)
    expect(clickSpy).not.toHaveBeenCalled()
    expect(probe()).toHaveAttribute('data-status', 'idle')

    clickSpy.mockRestore()
    root.remove()
    delete globalThis.MediaRecorder
  })

  it('has no axe violations, locked or playing', async () => {
    const locked = renderPanel({ canPlay: false })
    expect(await axe(locked.container)).toHaveNoViolations()
    locked.unmount()

    const playing = renderPanel()
    await playToFrames()
    expect(await axe(playing.container)).toHaveNoViolations()
  })
})
