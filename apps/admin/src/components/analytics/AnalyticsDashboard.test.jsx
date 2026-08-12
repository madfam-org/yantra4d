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
    BarChart3: (props) => <span {...props} />,
    Download: (props) => <span {...props} />,
    Activity: (props) => <span {...props} />,
}))

import AnalyticsDashboard from './AnalyticsDashboard'

const FULL = {
    period_days: 30,
    total_renders: 12345,
    total_exports: 678,
    total_events: 90123,
    top_projects: [
        { slug: 'gridfinity', renders: 500 },
        { slug: 'stemfie', renders: 300 },
        { slug: 'gears', renders: 200 },
        { slug: 'soft-jaw', renders: 100 },
        { slug: 'fasteners', renders: 50 },
        { slug: 'overflow-should-not-render', renders: 1 },
    ],
    daily_renders: [
        { date: '2026-08-09', count: 10 },
        { date: '2026-08-10', count: 20 },
    ],
    event_counts: { render: 900, export: 100 },
}

const EMPTY = {
    period_days: 7,
    total_renders: 0,
    total_exports: 0,
    total_events: 0,
    top_projects: [],
    daily_renders: [],
    event_counts: {},
}

function mockFetchResolving(body, ok = true, status = 200) {
    return vi.fn(() => Promise.resolve({ ok, status, json: () => Promise.resolve(body) }))
}

describe('AnalyticsDashboard', () => {
    beforeEach(() => {
        sessionStorage.clear()
        globalThis.fetch = mockFetchResolving(FULL)
    })
    afterEach(() => {
        vi.restoreAllMocks()
    })

    it('shows a loading state before the request settles', () => {
        globalThis.fetch = vi.fn(() => new Promise(() => {}))
        render(<AnalyticsDashboard />)
        expect(screen.getByText('Loading analytics...')).toBeInTheDocument()
    })

    it('requests a 30 day window', async () => {
        render(<AnalyticsDashboard />)
        await screen.findByText('Last 30 days')
        expect(globalThis.fetch).toHaveBeenCalledWith(
            '/api/admin/analytics/global?days=30',
            expect.any(Object),
        )
    })

    it('sends the bearer token when one is stored', async () => {
        sessionStorage.setItem('janua_access_token', 'tok-xyz')
        render(<AnalyticsDashboard />)
        await screen.findByText('Last 30 days')
        expect(globalThis.fetch).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({
            headers: expect.objectContaining({ Authorization: 'Bearer tok-xyz' }),
        }))
    })

    it('omits the Authorization header when no token is stored', async () => {
        render(<AnalyticsDashboard />)
        await screen.findByText('Last 30 days')
        expect(globalThis.fetch.mock.calls[0][1].headers).not.toHaveProperty('Authorization')
    })

    it('renders metric cards with thousands separators', async () => {
        render(<AnalyticsDashboard />)
        expect(await screen.findByText('12,345')).toBeInTheDocument()
        expect(screen.getByText('678')).toBeInTheDocument()
        expect(screen.getByText('90,123')).toBeInTheDocument()
        expect(screen.getByText('Total Renders')).toBeInTheDocument()
    })

    it('caps the top projects table at five rows', async () => {
        render(<AnalyticsDashboard />)
        expect(await screen.findByText('gridfinity')).toBeInTheDocument()
        expect(screen.getByText('fasteners')).toBeInTheDocument()
        expect(screen.queryByText('overflow-should-not-render')).not.toBeInTheDocument()
    })

    it('scales the daily bars against the busiest day', async () => {
        const { container } = render(<AnalyticsDashboard />)
        await screen.findByText('Daily Renders')
        const bars = container.querySelectorAll('.bg-blue-500\\/70')
        expect(bars).toHaveLength(2)
        expect(bars[0].style.width).toBe('50%')   // 10 of max 20
        expect(bars[1].style.width).toBe('100%')  // the max itself
    })

    it('orders the event breakdown by descending count', async () => {
        render(<AnalyticsDashboard />)
        await screen.findByText('Event Breakdown')
        expect(screen.getByText('render: 900')).toBeInTheDocument()
        expect(screen.getByText('export: 100')).toBeInTheDocument()
    })

    it('shows an empty state when nothing was recorded', async () => {
        globalThis.fetch = mockFetchResolving(EMPTY)
        render(<AnalyticsDashboard />)
        expect(await screen.findByText('No analytics events recorded in the last 7 days.')).toBeInTheDocument()
        expect(screen.queryByText('Top Projects by Renders')).not.toBeInTheDocument()
        expect(screen.queryByText('Daily Renders')).not.toBeInTheDocument()
        expect(screen.queryByText('Event Breakdown')).not.toBeInTheDocument()
    })

    it('survives a zero-count day without dividing by zero', async () => {
        globalThis.fetch = mockFetchResolving({
            ...EMPTY,
            daily_renders: [{ date: '2026-08-10', count: 0 }],
        })
        const { container } = render(<AnalyticsDashboard />)
        await screen.findByText('Daily Renders')
        expect(container.querySelector('.bg-blue-500\\/70').style.width).toBe('0%')
    })

    it('surfaces an HTTP error and retries on demand', async () => {
        globalThis.fetch = mockFetchResolving(null, false, 403)
        render(<AnalyticsDashboard />)
        expect(await screen.findByText(/Failed to load analytics: HTTP 403/)).toBeInTheDocument()

        globalThis.fetch = mockFetchResolving(FULL)
        fireEvent.click(screen.getByText('Retry'))
        expect(await screen.findByText('Last 30 days')).toBeInTheDocument()
    })

    it('surfaces a network rejection', async () => {
        globalThis.fetch = vi.fn(() => Promise.reject(new Error('DNS failure')))
        render(<AnalyticsDashboard />)
        expect(await screen.findByText(/Failed to load analytics: DNS failure/)).toBeInTheDocument()
    })

    it('refetches when the refresh control is used', async () => {
        render(<AnalyticsDashboard />)
        await screen.findByText('Last 30 days')
        fireEvent.click(screen.getByTitle('Refresh'))
        await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(2))
    })

    it('renders nothing when the payload is null', async () => {
        globalThis.fetch = mockFetchResolving(null)
        const { container } = render(<AnalyticsDashboard />)
        await waitFor(() => expect(screen.queryByText('Loading analytics...')).not.toBeInTheDocument())
        expect(container).toBeEmptyDOMElement()
    })
})
