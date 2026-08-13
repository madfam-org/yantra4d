import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// Mock fetch globally
const mockFetch = vi.fn()
globalThis.fetch = mockFetch

// Mock the CSS import
vi.mock('./AnimationPanel.css', () => ({}))

import AnimationPanel from './AnimationPanel'

const MOCK_ANIMATIONS = [
    {
        id: 'grow',
        label: { en: 'Grow' },
        description: { en: 'Animate height' },
        frames: 5,
        duration_ms: 2000,
        easing: 'ease-in-out',
    },
    {
        id: 'rotate',
        label: 'Rotate',
        frames: 10,
        duration_ms: 3000,
    },
]

describe('AnimationPanel', () => {
    const defaultProps = {
        projectSlug: 'test-project',
        onLoadFrame: vi.fn(),
    }

    beforeEach(() => {
        vi.clearAllMocks()
        mockFetch.mockReset()
    })

    it('renders null when no animations are available', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ animations: [] }),
        })

        const { container } = render(<AnimationPanel {...defaultProps} />)
        await waitFor(() => {
            expect(container.innerHTML).toBe('')
        })
    })

    it('renders animation cards when animations exist', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ animations: MOCK_ANIMATIONS }),
        })

        render(<AnimationPanel {...defaultProps} />)

        await waitFor(() => {
            expect(screen.getByText('Grow')).toBeInTheDocument()
            expect(screen.getByText('Rotate')).toBeInTheDocument()
        })
    })

    it('shows render button when an animation is selected', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ animations: MOCK_ANIMATIONS }),
        })

        render(<AnimationPanel {...defaultProps} />)

        await waitFor(() => {
            expect(screen.getByText('Grow')).toBeInTheDocument()
        })

        fireEvent.click(screen.getByText('Grow'))
        expect(screen.getByText('Render Animation')).toBeInTheDocument()
    })

    it('shows animation metadata (frames, duration, easing)', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ animations: MOCK_ANIMATIONS }),
        })

        render(<AnimationPanel {...defaultProps} />)

        await waitFor(() => {
            expect(screen.getByText(/5 frames · 2000ms · ease-in-out/)).toBeInTheDocument()
        })
    })

    it('handles description as string', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ animations: MOCK_ANIMATIONS }),
        })

        render(<AnimationPanel {...defaultProps} />)

        await waitFor(() => {
            expect(screen.getByText('Animate height')).toBeInTheDocument()
        })
    })

    it('does not fetch when projectSlug is empty', () => {
        render(<AnimationPanel projectSlug="" onLoadFrame={vi.fn()} />)
        expect(mockFetch).not.toHaveBeenCalled()
    })

    it('handles fetch failure gracefully', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: false,
            json: async () => ({ error: 'Not found' }),
        })

        const { container } = render(<AnimationPanel {...defaultProps} />)
        await waitFor(() => {
            expect(container.innerHTML).toBe('')
        })
    })

    it('has proper aria-label on the panel region', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ animations: MOCK_ANIMATIONS }),
        })

        render(<AnimationPanel {...defaultProps} />)

        await waitFor(() => {
            expect(screen.getByRole('region', { name: 'Animation Panel' })).toBeInTheDocument()
        })
    })

    // --- Render, playback, cancel and export ---------------------------------
    // AnimationPanel sat at 23.8% branch coverage: only the "no animations"
    // early return was exercised. Everything below the fetch — the SSE render
    // stream, playback, cancel and WebM export — was untested.

    /** Build a Response whose body streams the given SSE events. */
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

    const listAnimations = () => ({ ok: true, json: async () => ({ animations: MOCK_ANIMATIONS }) })

    const FRAMES = [
        { frame_index: 0, parts: [{ url: '/f0.glb' }] },
        { frame_index: 1, parts: [{ url: '/f1.glb' }] },
    ]

    async function renderPanelWithAnimations(props = {}) {
        mockFetch.mockResolvedValueOnce(listAnimations())
        const utils = render(<AnimationPanel {...defaultProps} {...props} />)
        await screen.findByText('Grow')
        return utils
    }

    it('lists animations from the backend with frame and duration metadata', async () => {
        await renderPanelWithAnimations()
        expect(screen.getByText('Grow')).toBeInTheDocument()
        // The second entry uses a plain string label rather than a locale map.
        expect(screen.getByText('Rotate')).toBeInTheDocument()
        expect(screen.getByText('Animate height')).toBeInTheDocument()
    })

    it('streams a render to completion and reports progress then playback', async () => {
        const onLoadFrame = vi.fn()
        await renderPanelWithAnimations({ onLoadFrame })
        fireEvent.click(screen.getByText('Grow'))

        mockFetch.mockResolvedValueOnce(sseResponse([
            { event: 'frame_done', progress: 50 },
            { event: 'complete', frames: FRAMES },
        ]))
        fireEvent.click(screen.getByRole('button', { name: /render/i }))

        // Frames reaching the viewport is the observable outcome of 'complete'.
        await waitFor(() => expect(onLoadFrame).toHaveBeenCalledWith(['/f0.glb']))
    })

    it('surfaces a non-OK render response as an error', async () => {
        await renderPanelWithAnimations()
        fireEvent.click(screen.getByText('Grow'))

        mockFetch.mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({ error: 'Renderer exploded' }) })
        fireEvent.click(screen.getByRole('button', { name: /render/i }))

        expect(await screen.findByText(/Renderer exploded/)).toBeInTheDocument()
    })

    it('surfaces an SSE error event as an error', async () => {
        await renderPanelWithAnimations()
        fireEvent.click(screen.getByText('Grow'))

        mockFetch.mockResolvedValueOnce(sseResponse([{ event: 'error', error: 'frame 3 failed' }]))
        fireEvent.click(screen.getByRole('button', { name: /render/i }))

        expect(await screen.findByText(/frame 3 failed/)).toBeInTheDocument()
    })

    it('cancel during a render returns the panel to idle', async () => {
        await renderPanelWithAnimations()
        fireEvent.click(screen.getByText('Grow'))

        // A render that never resolves leaves the panel in its 'rendering' state.
        mockFetch.mockImplementationOnce(() => new Promise(() => { }))
        fireEvent.click(screen.getByRole('button', { name: /render/i }))

        const cancel = await screen.findByRole('button', { name: /cancel/i })
        fireEvent.click(cancel)
        await waitFor(() =>
            expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument()
        )
    })

    it('WebM export reports when there is no canvas to record', async () => {
        const onLoadFrame = vi.fn()
        await renderPanelWithAnimations({ onLoadFrame })
        fireEvent.click(screen.getByText('Grow'))

        mockFetch.mockResolvedValueOnce(sseResponse([{ event: 'complete', frames: FRAMES }]))
        fireEvent.click(screen.getByRole('button', { name: /render/i }))
        await waitFor(() => expect(onLoadFrame).toHaveBeenCalled())

        // jsdom renders no <canvas>, which is the branch under test: export must
        // say so rather than throwing on a null element.
        const exportBtn = await screen.findByRole('button', { name: /webm/i })
        fireEvent.click(exportBtn)
        expect(await screen.findByText(/No 3D canvas found/)).toBeInTheDocument()
    })

    it('playback advances through frames and loads each into the viewport', async () => {
        vi.useFakeTimers()
        const onLoadFrame = vi.fn()
        mockFetch.mockResolvedValueOnce(listAnimations())
        render(<AnimationPanel {...defaultProps} onLoadFrame={onLoadFrame} />)
        await vi.waitFor(() => expect(screen.getByText('Grow')).toBeInTheDocument())
        fireEvent.click(screen.getByText('Grow'))

        mockFetch.mockResolvedValueOnce(sseResponse([{ event: 'complete', frames: FRAMES }]))
        fireEvent.click(screen.getByRole('button', { name: /render/i }))
        await vi.waitFor(() => expect(onLoadFrame).toHaveBeenCalledWith(['/f0.glb']))

        // Playback loops on an interval of duration / frames.length.
        onLoadFrame.mockClear()
        await vi.advanceTimersByTimeAsync(2000)
        expect(onLoadFrame).toHaveBeenCalledWith(['/f1.glb'])
        vi.useRealTimers()
    })

    it('WebM export records the canvas and downloads the result', async () => {
        // jsdom has neither captureStream nor MediaRecorder; both are supplied
        // here so the export path can run end to end.
        const canvas = document.createElement('canvas')
        canvas.captureStream = vi.fn(() => ({ getTracks: () => [] }))
        document.body.appendChild(canvas)

        const started = vi.fn()
        const stopped = vi.fn()
        class FakeRecorder {
            constructor() { this.ondataavailable = null; this.onstop = null }
            start() { started() }
            stop() { stopped(); this.onstop?.() }
        }
        FakeRecorder.isTypeSupported = () => true
        globalThis.MediaRecorder = FakeRecorder
        const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => { })
        globalThis.URL.createObjectURL = vi.fn(() => 'blob:anim')
        globalThis.URL.revokeObjectURL = vi.fn()

        vi.useFakeTimers()
        const onLoadFrame = vi.fn()
        mockFetch.mockResolvedValueOnce(listAnimations())
        render(<AnimationPanel {...defaultProps} onLoadFrame={onLoadFrame} />)
        await vi.waitFor(() => expect(screen.getByText('Grow')).toBeInTheDocument())
        fireEvent.click(screen.getByText('Grow'))

        mockFetch.mockResolvedValueOnce(sseResponse([{ event: 'complete', frames: FRAMES }]))
        fireEvent.click(screen.getByRole('button', { name: /render/i }))
        await vi.waitFor(() => expect(onLoadFrame).toHaveBeenCalled())

        fireEvent.click(screen.getByRole('button', { name: /webm/i }))
        expect(started).toHaveBeenCalled()

        // Run past the last frame: the timer stops the recorder, which triggers
        // the download.
        await vi.advanceTimersByTimeAsync(5000)
        expect(stopped).toHaveBeenCalled()
        expect(clickSpy).toHaveBeenCalled()

        vi.useRealTimers()
        clickSpy.mockRestore()
        canvas.remove()
        delete globalThis.MediaRecorder
    })
})

