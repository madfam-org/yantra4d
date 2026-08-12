import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

vi.mock('@/components/ui/button', () => ({
    Button: ({ children, ...props }) => <button {...props}>{children}</button>,
}))
vi.mock('@/components/ui/badge', () => ({
    Badge: ({ children, variant, ...props }) => <span data-variant={variant} {...props}>{children}</span>,
}))
vi.mock('lucide-react', () => ({
    RefreshCw: (props) => <span {...props} />,
    AlertCircle: (props) => <span {...props} />,
    Loader2: (props) => <span {...props} />,
    Cpu: (props) => <span {...props} />,
    Info: (props) => <span {...props} />,
}))

import RenderQueuePanel from './RenderQueuePanel'

const BUSY = {
    active_renders: 2,
    recent: [
        { project: 'gridfinity', mode: 'cup', duration_ms: 1240 },
        { project: 'stemfie', mode: 'beam', duration_ms: 880 },
    ],
    note: 'Queue depth is sampled every 10s.',
}

function mockFetchResolving(body, ok = true, status = 200) {
    return vi.fn(() => Promise.resolve({ ok, status, json: () => Promise.resolve(body) }))
}

describe('RenderQueuePanel', () => {
    beforeEach(() => {
        sessionStorage.clear()
        globalThis.fetch = mockFetchResolving(BUSY)
    })
    afterEach(() => {
        vi.restoreAllMocks()
    })

    it('shows a loading state before the request settles', () => {
        globalThis.fetch = vi.fn(() => new Promise(() => {}))
        render(<RenderQueuePanel />)
        expect(screen.getByText('Loading render status...')).toBeInTheDocument()
    })

    it('queries the active renders endpoint', async () => {
        render(<RenderQueuePanel />)
        await screen.findByText('2 active')
        expect(globalThis.fetch).toHaveBeenCalledWith('/api/admin/renders/active', expect.any(Object))
    })

    it('sends the bearer token when one is stored', async () => {
        sessionStorage.setItem('janua_access_token', 'tok-abc')
        render(<RenderQueuePanel />)
        await screen.findByText('2 active')
        expect(globalThis.fetch).toHaveBeenCalledWith('/api/admin/renders/active', expect.objectContaining({
            headers: expect.objectContaining({ Authorization: 'Bearer tok-abc' }),
        }))
    })

    it('omits the Authorization header when no token is stored', async () => {
        render(<RenderQueuePanel />)
        await screen.findByText('2 active')
        expect(globalThis.fetch.mock.calls[0][1].headers).not.toHaveProperty('Authorization')
    })

    it('lists recent renders with their durations', async () => {
        render(<RenderQueuePanel />)
        expect(await screen.findByText('gridfinity')).toBeInTheDocument()
        expect(screen.getByText('stemfie')).toBeInTheDocument()
        expect(screen.getByText('1240ms')).toBeInTheDocument()
        expect(screen.getByText('Recent Renders')).toBeInTheDocument()
    })

    it('renders the integration note when present', async () => {
        render(<RenderQueuePanel />)
        expect(await screen.findByText('Queue depth is sampled every 10s.')).toBeInTheDocument()
    })

    it('uses the default badge variant while renders are active', async () => {
        render(<RenderQueuePanel />)
        const badge = await screen.findByText('2 active')
        expect(badge.getAttribute('data-variant')).toBe('default')
    })

    it('falls back to the secondary badge and empty state when idle', async () => {
        globalThis.fetch = mockFetchResolving({ active_renders: 0, recent: [] })
        render(<RenderQueuePanel />)
        const badge = await screen.findByText('0 active')
        expect(badge.getAttribute('data-variant')).toBe('secondary')
        expect(screen.getByText('No active renders at the moment.')).toBeInTheDocument()
    })

    it('shows the empty state when recent is absent entirely', async () => {
        globalThis.fetch = mockFetchResolving({ active_renders: 0 })
        render(<RenderQueuePanel />)
        expect(await screen.findByText('No active renders at the moment.')).toBeInTheDocument()
        expect(screen.queryByText('Recent Renders')).not.toBeInTheDocument()
    })

    it('omits the note block when the payload has none', async () => {
        globalThis.fetch = mockFetchResolving({ active_renders: 1, recent: [] })
        render(<RenderQueuePanel />)
        await screen.findByText('1 active')
        expect(screen.queryByText(/sampled every/)).not.toBeInTheDocument()
    })

    it('surfaces an HTTP error and retries on demand', async () => {
        globalThis.fetch = mockFetchResolving(null, false, 500)
        render(<RenderQueuePanel />)
        expect(await screen.findByText(/Failed to load render status: HTTP 500/)).toBeInTheDocument()

        globalThis.fetch = mockFetchResolving(BUSY)
        fireEvent.click(screen.getByText('Retry'))
        expect(await screen.findByText('2 active')).toBeInTheDocument()
    })

    it('surfaces a network rejection', async () => {
        globalThis.fetch = vi.fn(() => Promise.reject(new Error('connection reset')))
        render(<RenderQueuePanel />)
        expect(await screen.findByText(/Failed to load render status: connection reset/)).toBeInTheDocument()
    })

    it('refetches when the refresh control is used', async () => {
        render(<RenderQueuePanel />)
        await screen.findByText('2 active')
        fireEvent.click(screen.getByTitle('Refresh'))
        await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(2))
    })

    it('renders nothing when the payload is null', async () => {
        globalThis.fetch = mockFetchResolving(null)
        const { container } = render(<RenderQueuePanel />)
        await waitFor(() => expect(screen.queryByText('Loading render status...')).not.toBeInTheDocument())
        expect(container).toBeEmptyDOMElement()
    })
})
