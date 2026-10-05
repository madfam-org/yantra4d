import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

vi.mock('../../services/core/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('../../services/core/apiClient', () => ({
  apiFetch: vi.fn(),
}))

import { canWriteCartridge, useProjectMeta } from './useProjectMeta'
import { apiFetch } from '../../services/core/apiClient'

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

describe('useProjectMeta across a navigation', () => {
  it('never answers for the new slug with the previous slug\'s meta', async () => {
    let release
    apiFetch.mockImplementation((url) => (url.includes('/own-fork/')
      ? Promise.resolve({ ok: true, json: () => Promise.resolve({ source: { type: 'fork' }, can_write: true }) })
      : new Promise((resolve) => { release = () => resolve({ ok: true, json: () => Promise.resolve({ can_write: false }) }) })))

    const { result, rerender } = renderHook(({ slug }) => useProjectMeta(slug), { initialProps: { slug: 'own-fork' } })
    await waitFor(() => expect(result.current?.can_write).toBe(true))

    rerender({ slug: 'bed-extrusion-mount' })
    expect(result.current).toBeNull()
    expect(canWriteCartridge(result.current)).toBe(false)

    release()
    await waitFor(() => expect(result.current).toEqual({ can_write: false }))
  })
})

describe('canWriteCartridge', () => {
  it('is true only when the API said so', () => {
    expect(canWriteCartridge({ can_write: true })).toBe(true)
    expect(canWriteCartridge({ can_write: false })).toBe(false)
    expect(canWriteCartridge({ source: { type: 'fork' } })).toBe(false)
    expect(canWriteCartridge(null)).toBe(false)
  })
})
