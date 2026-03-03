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
})
