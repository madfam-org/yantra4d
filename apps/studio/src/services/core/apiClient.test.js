import { describe, it, expect, vi, beforeEach } from 'vitest'

// Need to reset module between tests since it has module-level state
let apiFetch, setTokenGetter

beforeEach(async () => {
  vi.restoreAllMocks()
  vi.resetModules()
  const mod = await import('./apiClient')
  apiFetch = mod.apiFetch
  setTokenGetter = mod.setTokenGetter
})

describe('apiFetch', () => {
  it('makes a basic fetch call', async () => {
    const mockResponse = { ok: true, headers: { get: () => null } }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(mockResponse)

    const res = await apiFetch('http://api/test')
    expect(res).toBe(mockResponse)
    expect(fetch).toHaveBeenCalledWith('http://api/test', expect.any(Object))
  })

  it('injects Authorization header when token getter is set', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, headers: { get: () => null } })
    setTokenGetter(async () => 'test-token')

    await apiFetch('http://api/test')
    expect(fetch).toHaveBeenCalledWith('http://api/test', expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer test-token' })
    }))
  })

  it('proceeds without auth if token getter returns null', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, headers: { get: () => null } })
    setTokenGetter(async () => null)

    await apiFetch('http://api/test')
    const call = fetch.mock.calls[0]
    expect(call[1].headers.Authorization).toBeUndefined()
  })

  it('proceeds without auth if token getter throws', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, headers: { get: () => null } })
    setTokenGetter(async () => { throw new Error('no token') })

    await apiFetch('http://api/test')
    expect(fetch).toHaveBeenCalled()
  })

  it('extracts rate limit headers', async () => {
    const headers = new Map([
      ['X-RateLimit-Limit', '100'],
      ['X-RateLimit-Remaining', '95'],
      ['X-RateLimit-Tier', 'pro'],
    ])
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: { get: (k) => headers.get(k) || null },
    })

    await apiFetch('http://api/test')
    // Rate limit state is updated internally — tested via useRateLimit hook
    expect(fetch).toHaveBeenCalled()
  })

  it('passes through custom options', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, headers: { get: () => null } })

    await apiFetch('http://api/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    })
    expect(fetch).toHaveBeenCalledWith('http://api/test', expect.objectContaining({
      method: 'POST',
      body: '{}',
    }))
  })

  it('handles partial rate limit headers (only remaining)', async () => {
    const headers = new Map([
      ['X-RateLimit-Remaining', '42'],
    ])
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: { get: (k) => headers.get(k) || null },
    })

    await apiFetch('http://api/test')
    expect(fetch).toHaveBeenCalled()
  })
})

describe('useRateLimit', () => {
  it('returns initial rate limit state', async () => {
    const { renderHook } = await import('@testing-library/react')
    const mod = await import('./apiClient')
    const { result } = renderHook(() => mod.useRateLimit())
    expect(result.current).toHaveProperty('remaining')
    expect(result.current).toHaveProperty('limit')
    expect(result.current).toHaveProperty('tier')
  })

  it('updates state when rate limit headers change', async () => {
    const { renderHook, act } = await import('@testing-library/react')
    const mod = await import('./apiClient')
    const { result } = renderHook(() => mod.useRateLimit())

    const headers = new Map([
      ['X-RateLimit-Limit', '200'],
      ['X-RateLimit-Remaining', '180'],
      ['X-RateLimit-Tier', 'madfam'],
    ])
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: { get: (k) => headers.get(k) || null },
    })

    await act(async () => {
      await mod.apiFetch('http://api/test')
    })

    expect(result.current.limit).toBe(200)
    expect(result.current.remaining).toBe(180)
    expect(result.current.tier).toBe('madfam')
  })
})
