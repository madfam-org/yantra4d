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

  it('sends the documented nested payload shape', async () => {
    const { fetchAssemblyGeometries } = await import('./assemblyFetcher')

    apiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        parts: [{ type: 'bottom', url: 'http://localhost:5000/static/bottom.stl' }],
      }),
    })

    await fetchAssemblyGeometries({ size: 110, target_material: 'pla' }, ['size'])
    const payload = JSON.parse(apiFetch.mock.calls[0][1].body)

    // Contract: {mode, parameters, parts, export_format?, project?} — NESTED.
    expect(payload.mode).toBe('assembly')
    expect(payload.parameters).toEqual({ size: 110, target_material: 'pla' })
    // Params must not leak to the top level (that form changes the server-side
    // param_hash / cache key and drops target_material).
    expect(payload.size).toBeUndefined()
    expect(payload.target_material).toBeUndefined()
  })

  it('includes project slug in payload when provided', async () => {
    const { fetchAssemblyGeometries } = await import('./assemblyFetcher')

    apiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        parts: [{ type: 'bottom', url: 'http://localhost:5000/static/bottom.stl' }],
      }),
    })

    await fetchAssemblyGeometries({ size: 80 }, ['size'], 'tablaco')
    const payload = JSON.parse(apiFetch.mock.calls[0][1].body)
    expect(payload.project).toBe('tablaco')
  })

  it('caches separately per project slug', async () => {
    const { fetchAssemblyGeometries } = await import('./assemblyFetcher')

    apiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        parts: [{ type: 'bottom', url: 'http://localhost:5000/static/bottom.stl' }],
      }),
    })

    // First call caches under project-a
    await fetchAssemblyGeometries({ size: 90 }, ['size'], 'project-a')
    expect(apiFetch).toHaveBeenCalledTimes(1)

    // Same params + same project should hit cache (no new fetch)
    await fetchAssemblyGeometries({ size: 90 }, ['size'], 'project-a')
    expect(apiFetch).toHaveBeenCalledTimes(1)

    // Same params but different project should miss cache (new fetch)
    // Don't await the result since the singleton Worker can't handle concurrent tasks
    fetchAssemblyGeometries({ size: 90 }, ['size'], 'project-b').catch(() => {})
    expect(apiFetch).toHaveBeenCalledTimes(2)
  })

  it('works without project slug (backward compatible)', async () => {
    const { fetchAssemblyGeometries } = await import('./assemblyFetcher')

    apiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        parts: [{ type: 'bottom', url: 'http://localhost:5000/static/bottom.stl' }],
      }),
    })

    await fetchAssemblyGeometries({ size: 100 }, ['size'])
    const payload = JSON.parse(apiFetch.mock.calls[0][1].body)
    expect(payload.project).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// Settling: every parse path must resolve or reject — a pending promise is the
// bug the animated grid hung on ("preparing" with nothing left to wait for).
// ---------------------------------------------------------------------------
describe('fetchAssemblyGeometries — settling', () => {
  /** A worker that never answers on its own; tests drive its listeners. */
  class SilentWorker {
    constructor() {
      this.listeners = {}
      this.addEventListener = vi.fn((type, fn) => { (this.listeners[type] ||= []).push(fn) })
      this.removeEventListener = vi.fn((type, fn) => {
        this.listeners[type] = (this.listeners[type] || []).filter(f => f !== fn)
      })
      this.terminate = vi.fn()
      this.postMessage = vi.fn()
    }
    emit(type, event) { for (const fn of [...(this.listeners[type] || [])]) fn(event) }
  }

  let workers
  const params = { size: 20 }
  const keys = ['size']

  async function loadFetcher() {
    workers = []
    globalThis.Worker = class extends SilentWorker { constructor() { super(); workers.push(this) } }
    apiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ parts: [{ type: 'body', url: '/renders/body.stl' }] }),
    })
    return import('./assemblyFetcher')
  }

  it('forwards the AbortSignal to the render request', async () => {
    const { fetchAssemblyGeometries } = await loadFetcher()
    const controller = new AbortController()
    const p = fetchAssemblyGeometries(params, keys, 'proj', { signal: controller.signal })
    await vi.waitFor(() => expect(apiFetch).toHaveBeenCalled())
    expect(apiFetch.mock.calls[0][1].signal).toBe(controller.signal)
    controller.abort()
    await expect(p).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('rejects with AbortError when aborted while the worker is parsing, and detaches its listener', async () => {
    const { fetchAssemblyGeometries } = await loadFetcher()
    const controller = new AbortController()
    const p = fetchAssemblyGeometries(params, keys, undefined, { signal: controller.signal })
    await vi.waitFor(() => expect(workers[0]?.postMessage).toHaveBeenCalled())
    controller.abort()
    await expect(p).rejects.toMatchObject({ name: 'AbortError' })
    expect(workers[0].listeners.message).toHaveLength(0)
    expect(workers[0].listeners.error).toHaveLength(0)
  })

  it('rejects when the worker dies, and starts a fresh worker for the next parse', async () => {
    const { fetchAssemblyGeometries } = await loadFetcher()
    const p = fetchAssemblyGeometries(params, keys)
    await vi.waitFor(() => expect(workers[0]?.postMessage).toHaveBeenCalled())
    workers[0].emit('error', { message: 'out of memory' })
    await expect(p).rejects.toThrow('STL worker failed: out of memory')
    expect(workers[0].terminate).toHaveBeenCalled()
    // next call spawns a new worker instead of reusing the dead one
    const p2 = fetchAssemblyGeometries({ size: 21 }, keys)
    await vi.waitFor(() => expect(workers).toHaveLength(2))
    workers[1].emit('error', { message: 'again' })
    await expect(p2).rejects.toThrow('again')
  })

  it('rejects on messageerror instead of waiting forever', async () => {
    const { fetchAssemblyGeometries } = await loadFetcher()
    const p = fetchAssemblyGeometries(params, keys)
    await vi.waitFor(() => expect(workers[0]?.postMessage).toHaveBeenCalled())
    workers[0].emit('messageerror', {})
    await expect(p).rejects.toThrow('could not be deserialized')
  })

  it('rejects after STL_PARSE_TIMEOUT_MS when the worker never answers', async () => {
    vi.useFakeTimers()
    try {
      const { fetchAssemblyGeometries, STL_PARSE_TIMEOUT_MS } = await loadFetcher()
      const p = fetchAssemblyGeometries(params, keys)
      // let the render POST resolve and the worker task start
      await vi.advanceTimersByTimeAsync(0)
      expect(workers[0].postMessage).toHaveBeenCalled()
      const rejection = expect(p).rejects.toThrow('STL parse timed out')
      await vi.advanceTimersByTimeAsync(STL_PARSE_TIMEOUT_MS + 1)
      await rejection
      expect(workers[0].terminate).toHaveBeenCalled()
    } finally {
      vi.useRealTimers()
    }
  })

  it('does not cache a result the aborted caller never consumed', async () => {
    const { fetchAssemblyGeometries } = await loadFetcher()
    const controller = new AbortController()
    const p = fetchAssemblyGeometries(params, keys, undefined, { signal: controller.signal })
    await vi.waitFor(() => expect(workers[0]?.postMessage).toHaveBeenCalled())
    const { id } = workers[0].postMessage.mock.calls[0][0]
    controller.abort()
    // a late success from the worker must not resurrect the aborted call
    workers[0].emit('message', { data: { id, success: true, geometryData: { positions: new Float32Array(9) } } })
    await expect(p).rejects.toMatchObject({ name: 'AbortError' })
    // a fresh, un-aborted call with the same params must fetch again (nothing was cached)
    apiFetch.mockClear()
    const p2 = fetchAssemblyGeometries(params, keys)
    await vi.waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1))
    await vi.waitFor(() => expect(workers[0].postMessage).toHaveBeenCalledTimes(2))
    const { id: id2 } = workers[0].postMessage.mock.calls[1][0]
    workers[0].emit('message', { data: { id: id2, success: true, geometryData: { positions: new Float32Array(9) } } })
    await expect(p2).resolves.toHaveLength(1)
  })
})
