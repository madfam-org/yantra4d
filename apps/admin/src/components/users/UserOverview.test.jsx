import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

vi.mock('@/components/ui/button', () => ({
    Button: ({ children, ...props }) => <button {...props}>{children}</button>,
}))
vi.mock('@/components/ui/badge', () => ({
    Badge: ({ children, ...props }) => <span {...props}>{children}</span>,
}))
vi.mock('lucide-react', () => ({
    RefreshCw: (props) => <span {...props} />,
    AlertCircle: (props) => <span {...props} />,
    Loader2: (props) => <span {...props} />,
    Users: (props) => <span {...props} />,
    Info: (props) => <span {...props} />,
    Shield: (props) => <span {...props} />,
}))

import UserOverview from './UserOverview'

const TIERS_OBJECT = {
    guest: { backend_renders_per_hour: 5, max_projects: 1, export_formats: ['stl'], ai_requests_per_hour: 0 },
    pro: { renders_per_hour: 100, max_projects: -1, export_formats: 'stl, step, glb', ai_requests_per_hour: 50 },
}

function mockFetchResolving(body, ok = true, status = 200) {
    return vi.fn(() => Promise.resolve({
        ok,
        status,
        json: () => Promise.resolve(body),
    }))
}

describe('UserOverview', () => {
    beforeEach(() => {
        sessionStorage.clear()
        globalThis.fetch = mockFetchResolving(TIERS_OBJECT)
    })
    afterEach(() => {
        vi.restoreAllMocks()
    })

    it('shows a loading state before the request settles', () => {
        globalThis.fetch = vi.fn(() => new Promise(() => {}))
        render(<UserOverview />)
        expect(screen.getByText('Loading tier definitions...')).toBeInTheDocument()
    })

    it('renders a card per tier once loaded', async () => {
        render(<UserOverview />)
        expect(await screen.findByText('guest')).toBeInTheDocument()
        expect(screen.getByText('pro')).toBeInTheDocument()
        expect(screen.getByText('Tier Definitions')).toBeInTheDocument()
    })

    it('sends the bearer token when one is stored', async () => {
        sessionStorage.setItem('janua_access_token', 'tok-123')
        render(<UserOverview />)
        await screen.findByText('guest')
        expect(globalThis.fetch).toHaveBeenCalledWith('/api/tiers', expect.objectContaining({
            headers: expect.objectContaining({ Authorization: 'Bearer tok-123' }),
        }))
    })

    it('omits the Authorization header when no token is stored', async () => {
        render(<UserOverview />)
        await screen.findByText('guest')
        const { headers } = globalThis.fetch.mock.calls[0][1]
        expect(headers).not.toHaveProperty('Authorization')
    })

    it('renders "unlimited" rather than -1 for uncapped projects', async () => {
        render(<UserOverview />)
        expect(await screen.findByText('unlimited')).toBeInTheDocument()
    })

    it('falls back to renders_per_hour when backend_renders_per_hour is absent', async () => {
        render(<UserOverview />)
        await screen.findByText('pro')
        expect(screen.getByText('100')).toBeInTheDocument()
    })

    it('joins array export formats and passes strings through', async () => {
        render(<UserOverview />)
        await screen.findByText('guest')
        expect(screen.getByText('stl')).toBeInTheDocument()
        expect(screen.getByText('stl, step, glb')).toBeInTheDocument()
    })

    it('accepts an array payload as well as an object', async () => {
        globalThis.fetch = mockFetchResolving([
            { name: 'basic', max_projects: 3, ai_requests_per_hour: 10 },
        ])
        render(<UserOverview />)
        expect(await screen.findByText('basic')).toBeInTheDocument()
        expect(screen.getByText('3')).toBeInTheDocument()
    })

    it('surfaces an HTTP error and retries on demand', async () => {
        globalThis.fetch = mockFetchResolving(null, false, 503)
        render(<UserOverview />)
        expect(await screen.findByText(/Failed to load tiers: HTTP 503/)).toBeInTheDocument()

        globalThis.fetch = mockFetchResolving(TIERS_OBJECT)
        fireEvent.click(screen.getByText('Retry'))
        expect(await screen.findByText('guest')).toBeInTheDocument()
    })

    it('surfaces a network rejection', async () => {
        globalThis.fetch = vi.fn(() => Promise.reject(new Error('offline')))
        render(<UserOverview />)
        expect(await screen.findByText(/Failed to load tiers: offline/)).toBeInTheDocument()
    })

    it('refetches when the refresh control is used', async () => {
        render(<UserOverview />)
        await screen.findByText('guest')
        fireEvent.click(screen.getByTitle('Refresh'))
        await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(2))
    })

    it('renders nothing when the payload is null', async () => {
        globalThis.fetch = mockFetchResolving(null)
        const { container } = render(<UserOverview />)
        await waitFor(() => expect(screen.queryByText('Loading tier definitions...')).not.toBeInTheDocument())
        expect(container).toBeEmptyDOMElement()
    })

    it('falls back to a neutral colour for an unknown tier key', async () => {
        globalThis.fetch = mockFetchResolving({ enterprise: { max_projects: 9 } })
        render(<UserOverview />)
        const badge = await screen.findByText('enterprise')
        expect(badge.className).toContain('text-zinc-500')
    })
})
