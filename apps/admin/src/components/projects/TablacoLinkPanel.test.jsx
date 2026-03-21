import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

vi.mock('@/components/ui/button', () => ({
    Button: ({ children, asChild, ...props }) => {
        if (asChild) return <>{children}</>
        return <button {...props}>{children}</button>
    },
}))
vi.mock('@/components/ui/card', () => ({
    Card: ({ children, ...props }) => <div data-testid="card" {...props}>{children}</div>,
    CardContent: ({ children, ...props }) => <div {...props}>{children}</div>,
    CardDescription: ({ children, ...props }) => <p {...props}>{children}</p>,
    CardHeader: ({ children, ...props }) => <div {...props}>{children}</div>,
    CardTitle: ({ children, ...props }) => <h2 {...props}>{children}</h2>,
}))
vi.mock('lucide-react', () => ({
    Copy: (props) => <span {...props} />,
    Check: (props) => <span {...props} />,
    ExternalLink: (props) => <span {...props} />,
    AlertCircle: (props) => <span {...props} />,
    RefreshCw: (props) => <span {...props} />,
    Loader2: (props) => <span {...props} />,
}))

import TablacoLinkPanel from './TablacoLinkPanel'

describe('TablacoLinkPanel', () => {
    beforeEach(() => {
        vi.restoreAllMocks()
    })

    it('shows loading state initially', () => {
        globalThis.fetch = vi.fn(() => new Promise(() => {}))
        render(<TablacoLinkPanel />)
        expect(screen.getByText(/fetching tablaco link/i)).toBeInTheDocument()
    })

    it('displays public URL after successful fetch', async () => {
        globalThis.fetch = vi.fn().mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({
                public_url: 'https://app.yantra4d.com/project/tablaco?mode=storefront',
                studio_url: 'https://app.yantra4d.com/project/tablaco',
            }),
        })

        render(<TablacoLinkPanel />)
        await waitFor(() => {
            expect(screen.getByText('https://app.yantra4d.com/project/tablaco?mode=storefront')).toBeInTheDocument()
        })
    })

    it('displays card title', async () => {
        globalThis.fetch = vi.fn().mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ public_url: 'https://example.com' }),
        })
        render(<TablacoLinkPanel />)
        await waitFor(() => {
            expect(screen.getByText('Tablaco Public Storefront')).toBeInTheDocument()
        })
    })

    it('shows error state on fetch failure', async () => {
        globalThis.fetch = vi.fn().mockResolvedValueOnce({ ok: false, status: 403 })

        render(<TablacoLinkPanel />)
        await waitFor(() => {
            expect(screen.getByText(/failed to load link/i)).toBeInTheDocument()
        })
    })

    it('retry button triggers re-fetch', async () => {
        globalThis.fetch = vi.fn()
            .mockResolvedValueOnce({ ok: false, status: 500 })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ public_url: 'https://example.com' }),
            })

        render(<TablacoLinkPanel />)
        await waitFor(() => {
            expect(screen.getByText('Retry')).toBeInTheDocument()
        })

        fireEvent.click(screen.getByText('Retry'))
        await waitFor(() => {
            expect(screen.getByText('https://example.com')).toBeInTheDocument()
        })
    })

    it('has copy link button', async () => {
        globalThis.fetch = vi.fn().mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ public_url: 'https://example.com' }),
        })

        render(<TablacoLinkPanel />)
        await waitFor(() => {
            expect(screen.getByText('Copy link')).toBeInTheDocument()
        })
    })

    it('has preview link', async () => {
        globalThis.fetch = vi.fn().mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ public_url: 'https://example.com' }),
        })

        render(<TablacoLinkPanel />)
        await waitFor(() => {
            const previewLink = screen.getByText('Preview').closest('a')
            expect(previewLink).toHaveAttribute('href', 'https://example.com')
            expect(previewLink).toHaveAttribute('target', '_blank')
        })
    })

    it('displays security warning', async () => {
        globalThis.fetch = vi.fn().mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ public_url: 'https://example.com' }),
        })

        render(<TablacoLinkPanel />)
        await waitFor(() => {
            expect(screen.getByText(/grants access.*without authentication/i)).toBeInTheDocument()
        })
    })
})
