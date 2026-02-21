import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('./backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('./apiClient', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from './apiClient'

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
})
