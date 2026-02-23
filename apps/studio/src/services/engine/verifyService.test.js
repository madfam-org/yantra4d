import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../core/backendDetection', () => ({
  isBackendAvailable: vi.fn(),
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('manifold-3d', () => ({
  default: () => Promise.resolve({
    Manifold: class {
      constructor() { }
      status() { return 0 }
      getProperties() { return { volume: 1000.5, surfaceArea: 250.2 } }
      delete() { }
    },
    Mesh: class {
      constructor() { }
      delete() { }
    },
  }),
}))

vi.mock('../../lib/stl-utils', () => ({
  parseSTL: () => ({
    vertices: new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0]),
    faces: new Uint32Array([0, 1, 2]),
    faceCount: 1,
  }),
  getBoundingBox: () => ({ size: [10, 10, 5], min: [0, 0, 0], max: [10, 10, 5] }),
}))

let verifyService

beforeEach(async () => {
  vi.restoreAllMocks()
  vi.resetModules()
  verifyService = await import('./verifyService')
})

describe('verify', () => {
  it('in backend mode, calls /api/verify with mode', async () => {
    const { isBackendAvailable } = await import('../core/backendDetection')
    isBackendAvailable.mockResolvedValue(true)

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    // verifyBackend → response
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'passed', passed: true, output: 'ok', parts_checked: 1 }),
    })

    const result = await verifyService.verify([{ type: 'main', url: 'http://x/a.stl' }], 'unit')

    expect(result.passed).toBe(true)
    expect(fetchMock.mock.calls[0][0]).toContain('/api/verify')
  })

  it('in backend mode, sends project slug when provided', async () => {
    const { isBackendAvailable } = await import('../core/backendDetection')
    isBackendAvailable.mockResolvedValue(true)

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'passed', passed: true, output: 'ok', parts_checked: 1 }),
    })

    await verifyService.verify([{ type: 'main', url: 'http://x/a.stl' }], 'unit', 'my-project')

    const verifyCall = fetchMock.mock.calls[0]
    const body = JSON.parse(verifyCall[1].body)
    expect(body.project).toBe('my-project')
    expect(body.mode).toBe('unit')
  })

  it('in backend mode, omits project field when not provided', async () => {
    const { isBackendAvailable } = await import('../core/backendDetection')
    isBackendAvailable.mockResolvedValue(true)

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'passed', passed: true, output: 'ok', parts_checked: 1 }),
    })

    await verifyService.verify([], 'unit')

    const verifyCall = fetchMock.mock.calls[0]
    const body = JSON.parse(verifyCall[1].body)
    expect(body.project).toBeUndefined()
    expect(body.mode).toBe('unit')
  })

  it('in backend mode, throws on non-ok response', async () => {
    const { isBackendAvailable } = await import('../core/backendDetection')
    isBackendAvailable.mockResolvedValue(true)

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: false, status: 500 }) // verify fails

    await expect(verifyService.verify([], 'unit')).rejects.toThrow('Verification failed: 500')
  })

  it('in client mode, throws on non-ok STL fetch', async () => {
    const { isBackendAvailable } = await import('../core/backendDetection')
    isBackendAvailable.mockResolvedValue(false)

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    // STL fetch returns 404
    fetchMock.mockResolvedValueOnce({ ok: false, status: 404 })

    const result = await verifyService.verify(
      [{ type: 'main', url: 'http://x/missing.stl' }],
      'unit'
    )

    expect(result.passed).toBe(false)
    expect(result.output).toContain('Failed to fetch STL for main: HTTP 404')
  })

  it('checkBackend is called through verify', async () => {
    const { isBackendAvailable } = await import('../core/backendDetection')
    isBackendAvailable.mockResolvedValue(true)

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'passed', passed: true, output: '', parts_checked: 0 }),
    })

    await verifyService.verify([], 'unit')
    await verifyService.verify([], 'unit')

    expect(isBackendAvailable).toHaveBeenCalled()
  })
})

describe('verify (client mode — manifold-3d path)', () => {
  // The manifold-3d mock is now at the top level.
  // The stl-utils mock is also at the top level.

  it('in client mode, passes when manifold check succeeds', async () => {
    const { isBackendAvailable } = await import('../core/backendDetection')
    isBackendAvailable.mockResolvedValue(false)

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(200)),
    })

    const result = await verifyService.verify(
      [{ type: 'main', url: 'http://x/main.stl' }],
      'unit'
    )
    expect(result.passed).toBe(true)
    expect(result.status).toBe('passed')
    expect(result.parts_checked).toBe(1)
    expect(result.output).toContain('Volume:')
  })

  it('in client mode, fails when manifold check returns non-zero status', async () => {
    const { isBackendAvailable } = await import('../core/backendDetection')
    isBackendAvailable.mockResolvedValue(false)

    // Re-mock manifold for this specific test failure
    const Module = await import('manifold-3d')
    vi.spyOn(Module, 'default').mockResolvedValueOnce({
      Manifold: class {
        status() { return 1 } // 1 = non-manifold
        getProperties() { return { volume: 500, surfaceArea: 100 } }
        delete() { }
      },
      Mesh: class {
        constructor() { }
        delete() { }
      },
    })

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({
      ok: true,
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(200)),
    })

    const result = await verifyService.verify(
      [{ type: 'main', url: 'http://x/main.stl' }],
      'unit'
    )
    expect(result.passed).toBe(false)
    expect(result.output).toContain('non-manifold')
  })

  it('in client mode, handles empty parts array gracefully', async () => {
    const { isBackendAvailable } = await import('../core/backendDetection')
    isBackendAvailable.mockResolvedValue(false)

    const result = await verifyService.verify([], 'unit')
    expect(result.passed).toBe(true)
    expect(result.parts_checked).toBe(0)
  })
})
