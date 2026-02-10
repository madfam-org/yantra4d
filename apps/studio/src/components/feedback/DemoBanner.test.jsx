import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

let mockIsAuthEnabled = true
let mockIsAuthenticated = false
let mockTier = 'guest'

vi.mock('../../contexts/AuthProvider', () => ({
  useAuth: () => ({ isAuthenticated: mockIsAuthenticated }),
  get isAuthEnabled() { return mockIsAuthEnabled },
}))

vi.mock('../../hooks/useTier', () => ({
  useTier: () => ({ tier: mockTier }),
}))

import DemoBanner from './DemoBanner'

beforeEach(() => {
  mockIsAuthEnabled = true
  mockIsAuthenticated = false
  mockTier = 'guest'
})

describe('DemoBanner', () => {
  it('renders for unauthenticated guest users', () => {
    render(<DemoBanner />)
    expect(screen.getByText(/demo mode/i)).toBeInTheDocument()
  })

  it('shows sign up link', () => {
    render(<DemoBanner />)
    expect(screen.getByText(/sign up/i)).toHaveAttribute('href', expect.stringContaining('pricing'))
  })

  it('dismiss button hides banner', () => {
    render(<DemoBanner />)
    fireEvent.click(screen.getByLabelText(/dismiss/i))
    expect(screen.queryByText(/demo mode/i)).not.toBeInTheDocument()
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
