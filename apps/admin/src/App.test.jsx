import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

// Mock hooks and components
vi.mock('./hooks/useJanuaAuth', () => ({
    useJanuaAuth: () => ({
        isLoading: false,
        isAuthenticated: true,
        user: { name: 'Admin' },
        logout: vi.fn(),
    }),
}))

vi.mock('./components/auth/AuthGuard', () => ({
    default: ({ children }) => <div data-testid="auth-guard">{children}</div>,
}))

vi.mock('./components/AdminShell', () => ({
    default: ({ auth }) => <div data-testid="admin-shell">Admin Shell</div>,
}))

import App from './App'

describe('App', () => {
    it('renders without crash', () => {
        render(<App />)
        expect(screen.getByTestId('auth-guard')).toBeInTheDocument()
        expect(screen.getByTestId('admin-shell')).toBeInTheDocument()
    })
})
