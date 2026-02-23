import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../core/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('../core/apiClient', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../core/apiClient'

const mockPostMessage = vi.fn()

class MockWorker {
  constructor() {
    this.addEventListener = vi.fn()
    this.removeEventListener = vi.fn()
  }

  postMessage(data) {
    mockPostMessage(data)
    // Find the message event listener
    const handlerCall = this.addEventListener.mock.calls.find(call => call[0] === 'message')
    if (handlerCall) {
      const handler = handlerCall[1]
      // Simulate success response immediately
      setTimeout(() => {
        handler({
          data: {
            id: data.id,
            success: true,
            geometryData: {
              positions: new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0]),
            }
          }
        })
      }, 0)
    }
  }
}

beforeEach(async () => {
  vi.clearAllMocks()
  vi.resetModules()
  globalThis.Worker = MockWorker
})

describe('fetchAssemblyGeometries', () => {
  it('fetches and parses assembly parts', async () => {
    const { fetchAssemblyGeometries } = await import('./assemblyFetcher')

    apiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        parts: [
          { type: 'bottom', url: 'http://localhost:5000/static/bottom.stl' },
        ],
      }),
    })

    const result = await fetchAssemblyGeometries({ size: 20 }, ['size'])
    expect(result).toHaveLength(1)
    expect(result[0].type).toBe('bottom')
  })

  it('throws on failed render', async () => {
    const { fetchAssemblyGeometries } = await import('./assemblyFetcher')

    apiFetch.mockResolvedValue({
      ok: false,
      status: 500,
    })

    await expect(fetchAssemblyGeometries({ size: 20 }, ['size'])).rejects.toThrow('Assembly render failed')
  })

  it('returns cached result on second call with same params', async () => {
    const { fetchAssemblyGeometries } = await import('./assemblyFetcher')

    apiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        parts: [{ type: 'bottom', url: 'http://localhost:5000/static/bottom.stl' }],
      }),
    })

    const result1 = await fetchAssemblyGeometries({ size: 30 }, ['size'])
    const result2 = await fetchAssemblyGeometries({ size: 30 }, ['size'])
    expect(result1).toBe(result2)
    // Only one fetch call since second is cached
    expect(apiFetch).toHaveBeenCalledTimes(1)
  })

  it('prepends API_BASE for relative URLs', async () => {
    const { fetchAssemblyGeometries } = await import('./assemblyFetcher')

    apiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        parts: [{ type: 'top', url: '/static/top.stl' }],
      }),
    })

    const result = await fetchAssemblyGeometries({ size: 40 }, ['size'])
    expect(result).toHaveLength(1)
    expect(result[0].type).toBe('top')
    // The worker should have received the full URL with API_BASE prepended
    const postCall = mockPostMessage.mock.calls[0][0]
    expect(postCall.url).toContain('http://localhost:5000/static/top.stl')
  })

  it('handles geometry data with normals', async () => {
    // Override MockWorker to return normals
    class MockWorkerWithNormals {
      constructor() {
        this.addEventListener = vi.fn()
        this.removeEventListener = vi.fn()
      }
      postMessage(data) {
        mockPostMessage(data)
        const handlerCall = this.addEventListener.mock.calls.find(call => call[0] === 'message')
        if (handlerCall) {
          setTimeout(() => {
            handlerCall[1]({
              data: {
                id: data.id,
                success: true,
                geometryData: {
                  positions: new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0]),
                  normals: new Float32Array([0, 0, 1, 0, 0, 1, 0, 0, 1]),
                }
              }
            })
          }, 0)
        }
      }
    }
    globalThis.Worker = MockWorkerWithNormals

    const { fetchAssemblyGeometries } = await import('./assemblyFetcher')

    apiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        parts: [{ type: 'body', url: 'http://localhost:5000/static/body.stl' }],
      }),
    })

    const result = await fetchAssemblyGeometries({ size: 50 }, ['size'])
    expect(result).toHaveLength(1)
    expect(result[0].type).toBe('body')
  })

  it('rejects when worker returns error', async () => {
    class MockWorkerError {
      constructor() {
        this.addEventListener = vi.fn()
        this.removeEventListener = vi.fn()
      }
      postMessage(data) {
        mockPostMessage(data)
        const handlerCall = this.addEventListener.mock.calls.find(call => call[0] === 'message')
        if (handlerCall) {
          setTimeout(() => {
            handlerCall[1]({
              data: {
                id: data.id,
                success: false,
                error: 'STL parse failed',
              }
            })
          }, 0)
        }
      }
    }
    globalThis.Worker = MockWorkerError

    const { fetchAssemblyGeometries } = await import('./assemblyFetcher')

    apiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        parts: [{ type: 'bottom', url: 'http://localhost:5000/static/bottom.stl' }],
      }),
    })

    await expect(fetchAssemblyGeometries({ size: 60 }, ['size'])).rejects.toThrow('STL parse failed')
  })

  it('only includes geometry keys that exist in params', async () => {
    const { fetchAssemblyGeometries } = await import('./assemblyFetcher')

    apiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        parts: [{ type: 'bottom', url: 'http://localhost:5000/static/bottom.stl' }],
      }),
    })

    // Pass extra params that are not in geometryKeys
    const result = await fetchAssemblyGeometries({ size: 70, color: 'red', depth: 5 }, ['size', 'depth'])
    expect(result).toHaveLength(1)
  })
})
