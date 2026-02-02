import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

vi.mock('../services/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('../services/apiClient', () => ({
  apiFetch: vi.fn(),
}))

import { useProjectMeta } from './useProjectMeta'
import { apiFetch } from '../services/apiClient'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useProjectMeta', () => {
  it('fetches meta for a slug', async () => {
    const meta = { source: { type: 'github', repo_url: 'https://github.com/u/r' } }
    apiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(meta) })

    const { result } = renderHook(() => useProjectMeta('my-project'))

    await waitFor(() => {
      expect(result.current).toEqual(meta)
    })
  })

  it('returns null if no slug', () => {
    const { result } = renderHook(() => useProjectMeta(null))
    expect(result.current).toBeNull()
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it('returns null on error', async () => {
    apiFetch.mockRejectedValue(new Error('network'))
    const { result } = renderHook(() => useProjectMeta('proj'))

    await waitFor(() => {
      expect(result.current).toBeNull()
    })
  })

  it('returns null on non-ok response', async () => {
    apiFetch.mockResolvedValue({ ok: false })
    const { result } = renderHook(() => useProjectMeta('proj'))

    await waitFor(() => {
      expect(result.current).toBeNull()
    })
  })
})
