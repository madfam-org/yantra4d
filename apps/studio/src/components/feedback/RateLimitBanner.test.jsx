import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

let mockRateLimit = { remaining: null, limit: null, tier: null }
let mockCanAccess = () => true
let mockIsAuthEnabled = true

vi.mock('../../services/core/apiClient', () => ({
  useRateLimit: () => mockRateLimit,
}))

vi.mock('../../hooks/system/useTier', () => ({
  useTier: () => ({ canAccess: mockCanAccess }),
}))

vi.mock('../../contexts/auth/AuthProvider', () => ({
  get isAuthEnabled() { return mockIsAuthEnabled },
}))

import RateLimitBanner from './RateLimitBanner'

beforeEach(() => {
  mockRateLimit = { remaining: null, limit: null, tier: null }
  mockCanAccess = () => true
  mockIsAuthEnabled = true
})

describe('RateLimitBanner', () => {
  it('hidden when no rate limit info', () => {
    const { container } = render(<RateLimitBanner />)
    expect(container.firstChild).toBeNull()
  })

  it('hidden when auth disabled', () => {
    mockIsAuthEnabled = false
    mockRateLimit = { remaining: 5, limit: 100, tier: 'pro' }
    const { container } = render(<RateLimitBanner />)
    expect(container.firstChild).toBeNull()
  })

  it('hidden when plenty remaining', () => {
    mockRateLimit = { remaining: 80, limit: 100, tier: 'pro' }
    const { container } = render(<RateLimitBanner />)
    expect(container.firstChild).toBeNull()
  })

  it('shows warning when low remaining', () => {
    mockRateLimit = { remaining: 5, limit: 100, tier: 'pro' }
    render(<RateLimitBanner />)
    expect(screen.getByText(/5 renders? remaining/i)).toBeInTheDocument()
  })

  it('shows exhausted message when remaining is 0', () => {
    mockRateLimit = { remaining: 0, limit: 100, tier: 'pro' }
    render(<RateLimitBanner />)
    expect(screen.getByText(/render limit reached/i)).toBeInTheDocument()
  })

  it('shows upgrade link for non-pro users', () => {
    mockRateLimit = { remaining: 0, limit: 30, tier: 'guest' }
    mockCanAccess = (tier) => tier === 'guest'
    render(<RateLimitBanner />)
    expect(screen.getByText(/sign up/i)).toBeInTheDocument()
  })
})
