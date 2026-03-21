import { describe, it, expect, vi } from 'vitest'

vi.mock('../../contexts/auth/TierProvider', () => ({
  useTier: () => ({
    tier: 'pro',
    canAccess: (t) => t !== 'madfam',
    loading: false,
    limits: { backend_renders_per_hour: 150 },
  }),
}))

import { useTier } from './useTier'

describe('useTier re-export', () => {
  it('re-exports useTier from TierProvider', () => {
    const result = useTier()
    expect(result.tier).toBe('pro')
    expect(result.canAccess('basic')).toBe(true)
    expect(result.canAccess('madfam')).toBe(false)
  })
})
