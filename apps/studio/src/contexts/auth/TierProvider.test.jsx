import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import React from 'react'

// Mock dependencies
vi.mock('../../services/core/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('../../services/core/apiClient', () => ({
  apiFetch: vi.fn(),
}))

const mockAuth = vi.hoisted(() => ({
  isAuthenticated: false,
  isAuthEnabled: false,
}))

vi.mock('./AuthProvider', () => ({
  useAuth: () => ({ isAuthenticated: mockAuth.isAuthenticated }),
  get isAuthEnabled() { return mockAuth.isAuthEnabled }
}))

describe('TierProvider tests', () => {
  let TierProvider, useTier

  beforeEach(async () => {
    vi.clearAllMocks()
    vi.resetModules() // Ensure fresh TierProvider with current mockAuth state
    const module = await import('./TierProvider')
    TierProvider = module.TierProvider
    useTier = module.useTier

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        guest: { backend_renders_per_hour: 10 },
        essentials: { backend_renders_per_hour: 30 },
        pro: { backend_renders_per_hour: 150 },
        madfam: { backend_renders_per_hour: 500 },
      }),
    })
  })

  const wrapper = ({ children }) => <TierProvider>{children}</TierProvider>

  describe('useTier with auth DISABLED', () => {
    beforeEach(() => {
      mockAuth.isAuthenticated = false
      mockAuth.isAuthEnabled = false
    })

    it('returns tier context with canAccess', async () => {
      const { apiFetch } = await import('../../services/core/apiClient')
      apiFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ tier: 'pro', limits: { backend_renders_per_hour: 150 } }),
      })

      const { result } = renderHook(() => useTier(), { wrapper })
      await waitFor(() => expect(result.current.loading).toBe(false))
      expect(typeof result.current.canAccess).toBe('function')
      expect(result.current.tier).toBe('pro')
    })

    it('canAccess returns true when auth disabled', async () => {
      const { apiFetch } = await import('../../services/core/apiClient')
      apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ tier: 'guest' }) })

      const { result } = renderHook(() => useTier(), { wrapper })
      await waitFor(() => expect(result.current.loading).toBe(false))
      expect(result.current.canAccess('madfam')).toBe(true)
    })
  })

  describe('useTier with auth ENABLED', () => {
    beforeEach(() => {
      mockAuth.isAuthenticated = true
      mockAuth.isAuthEnabled = true
    })

    it('canAccess respects tier hierarchy when auth is enabled', async () => {
      const { apiFetch } = await import('../../services/core/apiClient')
      apiFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ tier: 'essentials', limits: { backend_renders_per_hour: 30 } }),
      })

      const { result } = renderHook(() => useTier(), { wrapper })
      await waitFor(() => expect(result.current.loading).toBe(false))

      // essentials tier: can access guest + essentials, NOT pro/madfam
      expect(result.current.canAccess('guest')).toBe(true)
      expect(result.current.canAccess('essentials')).toBe(true)
      expect(result.current.canAccess('pro')).toBe(false)
      expect(result.current.canAccess('madfam')).toBe(false)
    })

    it('madfam tier can access everything', async () => {
      const { apiFetch } = await import('../../services/core/apiClient')
      apiFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ tier: 'madfam', limits: { backend_renders_per_hour: 500 } }),
      })

      const { result } = renderHook(() => useTier(), { wrapper })
      await waitFor(() => expect(result.current.loading).toBe(false))
      expect(result.current.canAccess('pro')).toBe(true)
      expect(result.current.canAccess('madfam')).toBe(true)
    })

    it('falls back to guest if /api/me fails', async () => {
      const { apiFetch } = await import('../../services/core/apiClient')
      apiFetch.mockRejectedValue(new Error('network error'))

      const { result } = renderHook(() => useTier(), { wrapper })
      await waitFor(() => expect(result.current.loading).toBe(false))
      expect(result.current.tier).toBe('guest')
    })
  })

  describe('useTier fallback', () => {
    it('returns fallback when used outside provider', () => {
      const { result } = renderHook(() => useTier())
      expect(result.current.tier).toBeDefined()
      expect(typeof result.current.canAccess).toBe('function')
    })
  })
})
