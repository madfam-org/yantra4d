import { describe, it, expect, vi, beforeEach } from 'vitest'
import { isBackendAvailable, getApiBase, resetDetection } from '../core/backendDetection'

beforeEach(() => {
  resetDetection()
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('isBackendAvailable', () => {
  it('returns true and caches when health check succeeds', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true })
    expect(await isBackendAvailable()).toBe(true)
    // Second call should not fetch again (within positive TTL)
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

  it('re-checks after negative TTL expires (30s)', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockRejectedValueOnce(new Error('network'))
    expect(await isBackendAvailable()).toBe(false)
    expect(fetchMock).toHaveBeenCalledTimes(1)

    // Within TTL — should return cached false without fetching
    vi.advanceTimersByTime(10_000)
    expect(await isBackendAvailable()).toBe(false)
    expect(fetchMock).toHaveBeenCalledTimes(1)

    // After TTL — should re-check
    vi.advanceTimersByTime(25_000) // total 35s > 30s TTL
    fetchMock.mockResolvedValueOnce({ ok: true })
    expect(await isBackendAvailable()).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('re-checks after positive TTL expires (5min)', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true })
    expect(await isBackendAvailable()).toBe(true)

    // Within positive TTL — cached
    vi.advanceTimersByTime(60_000) // 1 min
    expect(await isBackendAvailable()).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(1)

    // After positive TTL (5 min)
    vi.advanceTimersByTime(250_000) // total 310s > 300s
    fetchMock.mockResolvedValueOnce({ ok: false })
    expect(await isBackendAvailable()).toBe(false)
    expect(fetchMock).toHaveBeenCalledTimes(2)
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

  it('clears TTL timer so immediate re-check occurs', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockRejectedValueOnce(new Error('down'))
    expect(await isBackendAvailable()).toBe(false)

    // Without reset, within TTL would return cached
    resetDetection()
    fetchMock.mockResolvedValueOnce({ ok: true })
    expect(await isBackendAvailable()).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
