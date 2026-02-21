import { describe, it, expect, vi, beforeEach } from 'vitest'
import { isBackendAvailable, getApiBase, resetDetection } from '../core/backendDetection'

beforeEach(() => {
  resetDetection()
  vi.restoreAllMocks()
})

describe('isBackendAvailable', () => {
  it('returns true and caches when health check succeeds', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true })
    expect(await isBackendAvailable()).toBe(true)
    // Second call should not fetch again
    expect(await isBackendAvailable()).toBe(true)
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('returns false on fetch failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network'))
    expect(await isBackendAvailable()).toBe(false)
  })

  it('returns false when response is not ok', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false })
    expect(await isBackendAvailable()).toBe(false)
  })
})

describe('getApiBase', () => {
  it('returns default localhost URL', () => {
    expect(getApiBase()).toBe('')
  })
})

describe('resetDetection', () => {
  it('clears cached result so next call fetches again', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true })
    await isBackendAvailable()
    resetDetection()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false })
    expect(await isBackendAvailable()).toBe(false)
  })
})
