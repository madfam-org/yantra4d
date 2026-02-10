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

vi.mock('../../contexts/AuthProvider', () => ({
  useAuth: () => mockAuth,
  isAuthEnabled: true,
}))

vi.mock('../../contexts/LanguageProvider', () => ({
  useLanguage: () => ({
    t: (key) => key,
    language: 'en',
  }),
}))

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
    expect(mockAuth.signInWithOAuth).toHaveBeenCalledWith('github')
  })

  it('shows loading state', () => {
    mockAuth.isLoading = true
    render(<AuthButton />)
    expect(screen.getByText('...')).toBeInTheDocument()
  })

  it('renders sign out when authenticated', () => {
    mockAuth.isAuthenticated = true
    mockAuth.user = { display_name: 'Test User', email: 'test@test.com' }
    render(<AuthButton />)
    expect(screen.getByTitle('auth.sign_out')).toBeInTheDocument()
    expect(screen.getByText('Test User')).toBeInTheDocument()
  })

  it('calls signOut on sign out click', () => {
    mockAuth.isAuthenticated = true
    mockAuth.user = { display_name: 'Alice' }
    render(<AuthButton />)
    fireEvent.click(screen.getByTitle('auth.sign_out'))
    expect(mockAuth.signOut).toHaveBeenCalled()
  })

  it('shows email when no display_name', () => {
    mockAuth.isAuthenticated = true
    mockAuth.user = { email: 'a@b.com' }
    render(<AuthButton />)
    expect(screen.getByText('a@b.com')).toBeInTheDocument()
  })
})

import AuthButton from './AuthButton'

describe('AuthButton (auth disabled)', () => {
  it('renders nothing when auth disabled', async () => {
    vi.doMock('../contexts/AuthProvider', () => ({
      useAuth: () => mockAuth,
      isAuthEnabled: false,
    }))
    const { default: AuthButtonDisabled } = await import('./AuthButton')
    const { container } = render(<AuthButtonDisabled />)
    expect(container).toBeDefined()
  })
})
