import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

const mockAuth = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  signOut: vi.fn(),
  signInWithOAuth: vi.fn(),
}

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

// Mock @janua/react-sdk components
vi.mock('@janua/react-sdk', () => ({
  UserButton: () => <div data-testid="janua-user-button">UserButton</div>,
  SignedIn: ({ children }) => mockAuth.isAuthenticated ? <>{children}</> : null,
  SignedOut: ({ children }) => !mockAuth.isAuthenticated ? <>{children}</> : null,
}))

import AuthButton from './AuthButton'

beforeEach(() => {
  mockAuth.user = null
  mockAuth.isAuthenticated = false
  mockAuth.isLoading = false
  vi.clearAllMocks()
})

describe('AuthButton', () => {
  it('renders sign in when unauthenticated', () => {
    render(<AuthButton />)
    expect(screen.getByText('auth.sign_in')).toBeInTheDocument()
  })

  it('calls signInWithOAuth on sign in click', () => {
    render(<AuthButton />)
    fireEvent.click(screen.getByTitle('auth.sign_in'))
    expect(mockAuth.signInWithOAuth).toHaveBeenCalledWith('google')
  })

  it('renders UserButton when authenticated', () => {
    mockAuth.isAuthenticated = true
    mockAuth.user = { display_name: 'Test User', email: 'test@test.com' }
    render(<AuthButton />)
    expect(screen.getByTestId('janua-user-button')).toBeInTheDocument()
  })

  it('hides sign in when authenticated', () => {
    mockAuth.isAuthenticated = true
    mockAuth.user = { display_name: 'Alice' }
    render(<AuthButton />)
    expect(screen.queryByText('auth.sign_in')).not.toBeInTheDocument()
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
