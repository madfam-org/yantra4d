import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

vi.mock('@janua/ui', () => ({
    SignIn: ({ afterSignIn, onError, ...props }) => (
        <div data-testid="janua-signin" {...props}>Janua SignIn</div>
    ),
}))
vi.mock('@/components/ui/card', () => ({
    Card: ({ children, ...props }) => <div {...props}>{children}</div>,
    CardDescription: ({ children, ...props }) => <p {...props}>{children}</p>,
    CardFooter: ({ children, ...props }) => <div {...props}>{children}</div>,
    CardHeader: ({ children, ...props }) => <div {...props}>{children}</div>,
    CardTitle: ({ children, ...props }) => <h2 {...props}>{children}</h2>,
}))

import LoginPage from './LoginPage'

describe('LoginPage', () => {
    const defaultAuth = {
        isLoading: false,
        isAuthenticated: false,
    }

    it('renders the login page', () => {
        render(<LoginPage auth={defaultAuth} />)
        expect(screen.getByText('Admin Panel')).toBeInTheDocument()
    })

    it('shows Yantra4D branding', () => {
        render(<LoginPage auth={defaultAuth} />)
        expect(screen.getByText('Y4D')).toBeInTheDocument()
        expect(screen.getByText('Yantra4D Project Management')).toBeInTheDocument()
    })

    it('renders Janua SignIn component', () => {
        render(<LoginPage auth={defaultAuth} />)
        expect(screen.getByTestId('janua-signin')).toBeInTheDocument()
    })

    it('shows Janua attribution link', () => {
        render(<LoginPage auth={defaultAuth} />)
        const link = screen.getByText('Janua')
        expect(link).toHaveAttribute('href', 'https://github.com/madfam-org/janua')
        expect(link).toHaveAttribute('target', '_blank')
    })
})
