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
  it('releases its subscription when the consumer unmounts', async () => {
    const { renderHook } = await import('@testing-library/react')
    const mod = await import('./apiClient')
    const add = vi.spyOn(Set.prototype, 'add')
    const { unmount } = renderHook(() => mod.useRateLimit())
    const index = add.mock.calls.findIndex(([value]) =>
      typeof value === 'function' && value.name === 'listener')
    expect(index).toBeGreaterThanOrEqual(0)
    const listeners = add.mock.contexts[index]
    const listener = add.mock.calls[index][0]
    expect(listeners.has(listener)).toBe(true)
    unmount()
    expect(listeners.has(listener)).toBe(false)
  })

  it('returns initial rate limit state', async () => {
    const { renderHook } = await import('@testing-library/react')
    const mod = await import('./apiClient')
    const { result } = renderHook(() => mod.useRateLimit())
    expect(result.current).toHaveProperty('remaining')
    expect(result.current).toHaveProperty('limit')
    expect(result.current).toHaveProperty('tier')
  })

  it('treats an unlimited limit header as no ceiling', async () => {
    const { renderHook, act } = await import('@testing-library/react')
    const mod = await import('./apiClient')
    const { result } = renderHook(() => mod.useRateLimit())

    // An unlimited tier answers `unlimited` and sends no Remaining/Reset.
    const headers = new Map([
      ['X-RateLimit-Limit', 'unlimited'],
      ['X-RateLimit-Tier', 'premium'],
    ])
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: { get: (k) => headers.get(k) || null },
    })

    await act(async () => {
      await mod.apiFetch('http://api/api/render-stream')
    })

    // -1, not NaN: the same "no ceiling" sentinel the tier API uses.
    expect(result.current.limit).toBe(-1)
    expect(result.current.remaining).toBeNull()
    expect(mod.isRateLimitExhausted()).toBe(false)
  })

  it('updates state when rate limit headers change', async () => {
    const { renderHook, act } = await import('@testing-library/react')
    const mod = await import('./apiClient')
    const { result } = renderHook(() => mod.useRateLimit())

    const headers = new Map([
      ['X-RateLimit-Limit', '200'],
      ['X-RateLimit-Remaining', '180'],
      ['X-RateLimit-Tier', 'premium'],
    ])
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: { get: (k) => headers.get(k) || null },
    })

    await act(async () => {
      await mod.apiFetch('http://api/api/render-stream')
    })

    expect(result.current.limit).toBe(200)
    expect(result.current.remaining).toBe(180)
    expect(result.current.tier).toBe('premium')
  })
})


describe('render quota isolation', () => {
  it('ignores exhausted non-render quotas when deciding render placement', async () => {
    const { renderHook, act } = await import('@testing-library/react')
    const mod = await import('./apiClient')
    const { result, unmount } = renderHook(() => mod.useRateLimit())
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false, status: 429,
      headers: new Headers({ 'X-RateLimit-Limit': '500', 'X-RateLimit-Remaining': '0' }),
    })
    for (const path of ['/api/projects', '/api/estimate', '/api/render-cancel']) {
      await act(async () => { await mod.apiFetch(path) })
    }
    expect(result.current.remaining).toBeNull()
    expect(mod.isRateLimitExhausted()).toBe(false)
    unmount()
  })

  it.each(['/api/render', '/api/render-stream?request=1'])(
    'retains exhausted %s quota after artifact and catalog responses', async (path) => {
      const { renderHook, act } = await import('@testing-library/react')
      const mod = await import('./apiClient')
      const { result, unmount } = renderHook(() => mod.useRateLimit())
      const mockedFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: false, status: 429,
        headers: new Headers({ 'X-RateLimit-Limit': '10', 'X-RateLimit-Remaining': '0' }),
      }).mockResolvedValue({
        ok: true,
        headers: new Headers({ 'X-RateLimit-Limit': '500', 'X-RateLimit-Remaining': '499' }),
      })
      await act(async () => { await mod.apiFetch(path) })
      for (const other of ['/api/projects', '/api/artifacts/example.stl']) {
        await act(async () => { await mod.apiFetch(other) })
      }
      expect(mockedFetch).toHaveBeenCalledTimes(3)
      expect(result.current.limit).toBe(10)
      expect(result.current.remaining).toBe(0)
      expect(mod.isRateLimitExhausted()).toBe(true)
      unmount()
    },
  )
})
