import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

let mockIsAuthEnabled = true
let mockIsAuthenticated = false
let mockTier = 'guest'

vi.mock('../../contexts/auth/AuthProvider', () => ({
  useAuth: () => ({ isAuthenticated: mockIsAuthenticated }),
  get isAuthEnabled() { return mockIsAuthEnabled },
}))

vi.mock('../../hooks/system/useTier', () => ({
  useTier: () => ({ tier: mockTier }),
}))

vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({ t: (key) => key }),
}))

import DemoBanner from './DemoBanner'

beforeEach(() => {
  mockIsAuthEnabled = true
  mockIsAuthenticated = false
  mockTier = 'guest'
})

describe('DemoBanner', () => {
  it('renders for unauthenticated guest users', () => {
    const { container } = render(<DemoBanner />)
    expect(container.textContent).toContain('demo.welcome')
  })

  it('shows create account link', () => {
    render(<DemoBanner />)
    expect(screen.getByText('demo.create_account')).toHaveAttribute('href', expect.stringContaining('pricing'))
  })

  it('dismiss button hides banner', () => {
    render(<DemoBanner />)
    fireEvent.click(screen.getByLabelText(/dismiss/i))
    expect(screen.queryByText('demo.welcome')).not.toBeInTheDocument()
  })

  it('hidden when authenticated', () => {
    mockIsAuthenticated = true
    const { container } = render(<DemoBanner />)
    expect(container.firstChild).toBeNull()
  })

  it('hidden when tier is not guest', () => {
    mockTier = 'pro'
    const { container } = render(<DemoBanner />)
    expect(container.firstChild).toBeNull()
  })

  it('hidden when auth disabled', () => {
    mockIsAuthEnabled = false
    const { container } = render(<DemoBanner />)
    expect(container.firstChild).toBeNull()
  })
})
