import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

vi.mock('lucide-react', () => ({
    Loader2: (props) => <span data-testid="loader" {...props} />,
}))

import OAuthCallback from './OAuthCallback'

describe('OAuthCallback', () => {
    let originalSearch
    let originalPathname
    let replaceStateSpy

    const mockAuth = {
        handleOAuthCallback: vi.fn(),
    }

    beforeEach(() => {
        originalSearch = window.location.search
        originalPathname = window.location.pathname
        replaceStateSpy = vi.spyOn(window.history, 'replaceState').mockImplementation(() => { })
        mockAuth.handleOAuthCallback.mockReset()
    })

    afterEach(() => {
        Object.defineProperty(window, 'location', {
            writable: true,
            value: { ...window.location, search: originalSearch, pathname: originalPathname },
        })
        replaceStateSpy.mockRestore()
    })

    function setSearchParams(params) {
        Object.defineProperty(window, 'location', {
            writable: true,
            value: { ...window.location, search: '?' + new URLSearchParams(params).toString(), pathname: '/auth/callback' },
        })
    }

    it('shows loading spinner during token exchange', () => {
        setSearchParams({ code: 'abc123', state: 'xyz789' })
        mockAuth.handleOAuthCallback.mockReturnValue(new Promise(() => { })) // never resolves
        render(<OAuthCallback auth={mockAuth} />)
        expect(screen.getByText('Completing sign-in...')).toBeInTheDocument()
        expect(screen.getByTestId('loader')).toBeInTheDocument()
    })

    it('calls handleOAuthCallback with code and state', () => {
        setSearchParams({ code: 'abc123', state: 'xyz789' })
        mockAuth.handleOAuthCallback.mockResolvedValue(undefined)
        render(<OAuthCallback auth={mockAuth} />)
        expect(mockAuth.handleOAuthCallback).toHaveBeenCalledWith('abc123', 'xyz789')
    })

    it('shows error when code is missing', () => {
        setSearchParams({ state: 'xyz789' })
        render(<OAuthCallback auth={mockAuth} />)
        expect(screen.getByText('Authentication Failed')).toBeInTheDocument()
        expect(screen.getByText('Missing authorization code or state parameter.')).toBeInTheDocument()
    })

    it('shows error when state is missing', () => {
        setSearchParams({ code: 'abc123' })
        render(<OAuthCallback auth={mockAuth} />)
        expect(screen.getByText('Authentication Failed')).toBeInTheDocument()
    })

    it('shows error from OAuth provider error response', () => {
        setSearchParams({ error: 'access_denied', error_description: 'User denied consent' })
        render(<OAuthCallback auth={mockAuth} />)
        expect(screen.getByText('User denied consent')).toBeInTheDocument()
    })

    it('shows error when handleOAuthCallback rejects', async () => {
        setSearchParams({ code: 'abc123', state: 'xyz789' })
        mockAuth.handleOAuthCallback.mockRejectedValue(new Error('Invalid state'))
        render(<OAuthCallback auth={mockAuth} />)
        await waitFor(() => {
            expect(screen.getByText('Invalid state')).toBeInTheDocument()
        })
    })

    it('renders back to sign in link on error', () => {
        setSearchParams({ error: 'access_denied' })
        render(<OAuthCallback auth={mockAuth} />)
        const link = screen.getByText('Back to sign in')
        expect(link).toHaveAttribute('href', '/')
    })
})
