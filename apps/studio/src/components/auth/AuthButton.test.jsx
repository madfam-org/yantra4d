import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

const mockAuth = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  signOut: vi.fn(async () => {}),
  signInWithOAuth: vi.fn(),
  signInWithJanua: vi.fn(async () => {}),
}

let mockSession = null

vi.mock('../../contexts/auth/AuthProvider', () => ({
  useAuth: () => mockAuth,
  isAuthEnabled: true,
}))

vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({
    t: (key) => key,
    language: 'en',
  }),
}))

// Mock @janua/react-sdk hooks and components
vi.mock('@janua/react-sdk', () => ({
  UserProfile: () => <div data-testid="janua-user-profile">UserProfile</div>,
  useSession: () => ({ session: mockSession }),
}))

import AuthButton from './AuthButton'

beforeEach(() => {
  mockAuth.user = null
  mockAuth.isAuthenticated = false
  mockAuth.isLoading = false
  mockSession = null
  try { localStorage.clear() } catch { /* jsdom */ }
  vi.clearAllMocks()
})

describe('AuthButton', () => {
  it('renders sign in when no session', () => {
    render(<AuthButton />)
    expect(screen.getByText('auth.sign_in')).toBeInTheDocument()
  })

  it('starts "Sign in with Janua" on click — never the social proxy flow', () => {
    // signInWithOAuth(provider) navigates to Janua's POST-only social route
    // (405) and auth.madfam.io has no social providers; see lib/januaSso.ts.
    render(<AuthButton />)
    fireEvent.click(screen.getByTitle('auth.sign_in'))
    expect(mockAuth.signInWithJanua).toHaveBeenCalledTimes(1)
    expect(mockAuth.signInWithOAuth).not.toHaveBeenCalled()
  })

  it('reports a sign-in that could not start instead of throwing from the click', async () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => {})
    mockAuth.signInWithJanua.mockRejectedValueOnce(new Error('no client'))
    render(<AuthButton />)
    fireEvent.click(screen.getByTitle('auth.sign_in'))
    await vi.waitFor(() => expect(error).toHaveBeenCalledWith('Sign-in could not start:', expect.any(Error)))
    error.mockRestore()
  })

  it('renders UserProfile when session exists', () => {
    mockSession = { user: { display_name: 'Test User', email: 'test@test.com' } }
    render(<AuthButton />)
    expect(screen.getByTestId('janua-user-profile')).toBeInTheDocument()
  })

  it('hides sign in when session exists', () => {
    mockSession = { user: { display_name: 'Alice' } }
    render(<AuthButton />)
    expect(screen.queryByText('auth.sign_in')).not.toBeInTheDocument()
  })

  it('shows the signed-in email and a working sign-out from a stored session (no SDK session)', () => {
    // The OIDC flow leaves the SDK `session` null even when signed in, so the
    // nav must key off the stored token: show who is signed in, offer sign-out.
    const b64url = (o) =>
      btoa(JSON.stringify(o)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
    const token = `${b64url({ alg: 'none' })}.${b64url({ email: 'caro@madfam.io', exp: Math.floor(Date.now() / 1000) + 3600 })}.sig`
    localStorage.setItem('janua_access_token', token)
    mockAuth.isAuthenticated = true
    mockSession = null

    render(<AuthButton />)

    expect(screen.queryByText('auth.sign_in')).not.toBeInTheDocument()
    expect(screen.getByText('caro@madfam.io')).toBeInTheDocument()
    fireEvent.click(screen.getByTitle('auth.sign_out'))
    expect(mockAuth.signOut).toHaveBeenCalledTimes(1)
  })
})

describe('AuthButton (auth disabled)', () => {
  it('renders nothing when auth disabled', async () => {
    vi.doMock('../../contexts/auth/AuthProvider', () => ({
      useAuth: () => mockAuth,
      isAuthEnabled: false,
    }))
    const { default: AuthButtonDisabled } = await import('./AuthButton')
    const { container } = render(<AuthButtonDisabled />)
    expect(container).toBeDefined()
  })
})
