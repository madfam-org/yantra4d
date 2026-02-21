import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import React from 'react'

// Mock dependencies
vi.mock('../services/core/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('../services/core/apiClient', () => ({
  apiFetch: vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ tier: 'pro', user: { sub: '1' }, limits: { renders_per_hour: 200 } }),
  }),
}))

vi.mock('./AuthProvider', () => ({
  useAuth: () => ({ isAuthenticated: false }),
  isAuthEnabled: false,
}))

import { TierProvider, useTier } from './TierProvider'

beforeEach(() => {
  vi.clearAllMocks()
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({
      guest: { renders_per_hour: 30 },
      basic: { renders_per_hour: 50 },
      pro: { renders_per_hour: 200 },
      madfam: { renders_per_hour: 500 },
    }),
  })
})

function wrapper({ children }) {
  return <TierProvider>{children}</TierProvider>
}

describe('useTier', () => {
  it('returns tier context with canAccess', async () => {
    const { result } = renderHook(() => useTier(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(typeof result.current.canAccess).toBe('function')
    expect(typeof result.current.tier).toBe('string')
  })

  it('canAccess returns true when auth disabled', async () => {
    const { result } = renderHook(() => useTier(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Auth disabled -> canAccess always true
    expect(result.current.canAccess('madfam')).toBe(true)
  })

  it('returns tier from /api/me response', async () => {
    const { result } = renderHook(() => useTier(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // apiFetch mock returns tier: 'pro'
    expect(result.current.tier).toBe('pro')
  })
})

describe('useTier fallback', () => {
  it('returns fallback when used outside provider', () => {
    const { result } = renderHook(() => useTier())
    expect(result.current.tier).toBeDefined()
    expect(typeof result.current.canAccess).toBe('function')
  })
})
