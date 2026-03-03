import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

// Mock lucide-react
vi.mock('lucide-react', () => ({
    Loader2: (props) => <span data-testid="loader" {...props} />,
}))

// Mock LoginPage
vi.mock('./LoginPage', () => ({
    default: ({ auth }) => <div data-testid="login-page">Login</div>,
}))

import AuthGuard from './AuthGuard'

describe('AuthGuard', () => {
    it('shows loading spinner when auth is loading', () => {
        render(
            <AuthGuard auth={{ isLoading: true, isAuthenticated: false }}>
                <div>Admin Content</div>
            </AuthGuard>
        )
        expect(screen.getByText('Verifying credentials…')).toBeInTheDocument()
        expect(screen.queryByText('Admin Content')).not.toBeInTheDocument()
    })

    it('shows login page when not authenticated', () => {
        render(
            <AuthGuard auth={{ isLoading: false, isAuthenticated: false }}>
                <div>Admin Content</div>
            </AuthGuard>
        )
        expect(screen.getByTestId('login-page')).toBeInTheDocument()
        expect(screen.queryByText('Admin Content')).not.toBeInTheDocument()
    })

    it('renders children when authenticated', () => {
        render(
            <AuthGuard auth={{ isLoading: false, isAuthenticated: true }}>
                <div>Admin Content</div>
            </AuthGuard>
        )
        expect(screen.getByText('Admin Content')).toBeInTheDocument()
    })
})
