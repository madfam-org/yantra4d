import { describe, it, expect, vi, beforeEach } from 'vitest'

let verifyService

beforeEach(async () => {
  vi.restoreAllMocks()
  vi.resetModules()
  verifyService = await import('./verifyService')
})

describe('verify', () => {
  it('in backend mode, calls /api/verify with mode', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    // checkBackend → ok
    fetchMock.mockResolvedValueOnce({ ok: true })
    // verifyBackend → response
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'passed', passed: true, output: 'ok', parts_checked: 1 }),
    })

    const result = await verifyService.verify([{ type: 'main', url: 'http://x/a.stl' }], 'unit')

    expect(result.passed).toBe(true)
    expect(fetchMock.mock.calls[1][0]).toContain('/api/verify')
  })

  it('in backend mode, throws on non-ok response', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health
    fetchMock.mockResolvedValueOnce({ ok: false, status: 500 }) // verify fails

    await expect(verifyService.verify([], 'unit')).rejects.toThrow('Verification failed: 500')
  })

  it('in client mode, throws on non-ok STL fetch', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockRejectedValueOnce(new Error('unreachable')) // health → wasm mode

    // STL fetch returns 404
    fetchMock.mockResolvedValueOnce({ ok: false, status: 404 })

    const result = await verifyService.verify(
      [{ type: 'main', url: 'http://x/missing.stl' }],
      'unit'
    )

    expect(result.passed).toBe(false)
    expect(result.output).toContain('Failed to fetch STL for main: HTTP 404')
  })

  it('checkBackend caches result on second call', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // first health
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'passed', passed: true, output: '', parts_checked: 0 }),
    })
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'passed', passed: true, output: '', parts_checked: 0 }),
    })

    await verifyService.verify([], 'unit')
    await verifyService.verify([], 'unit')

    // Health check only called once (cached), verify called twice
    const healthCalls = fetchMock.mock.calls.filter(c => c[0].toString().includes('/api/health'))
    expect(healthCalls).toHaveLength(1)
  })
})
