import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

let capturedSignInProps = {}
vi.mock('@janua/ui', () => ({
    SignIn: (props) => {
        capturedSignInProps = props
        return <div data-testid="janua-signin">Janua SignIn</div>
    },
}))

import LoginPage from './LoginPage'

describe('LoginPage', () => {
    const defaultAuth = {
        isLoading: false,
        isAuthenticated: false,
        signIn: vi.fn(),
        signOut: vi.fn(),
        signInWithOAuth: vi.fn(),
        handleOAuthCallback: vi.fn(),
        error: null,
        clearError: vi.fn(),
    }

    beforeEach(() => {
        capturedSignInProps = {}
    })

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

    it('passes SSO and social provider config to SignIn', () => {
        render(<LoginPage auth={defaultAuth} />)
        expect(capturedSignInProps.enableJanuaSSO).toBe(true)
        expect(capturedSignInProps.socialProviders).toEqual({
            google: true,
            github: true,
            microsoft: false,
            apple: false,
        })
        expect(capturedSignInProps.showRememberMe).toBe(true)
        expect(capturedSignInProps.termsUrl).toBe('https://madfam.io/terms')
        expect(capturedSignInProps.privacyUrl).toBe('https://madfam.io/privacy')
    })
})
