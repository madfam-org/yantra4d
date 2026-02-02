import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('./backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('./apiClient', () => ({
  apiFetch: vi.fn(),
}))

// Mock THREE's STLLoader
vi.mock('three/examples/jsm/loaders/STLLoader', () => ({
  STLLoader: class {
    parse() {
      return { computeVertexNormals: vi.fn() }
    }
  },
}))

import { apiFetch } from './apiClient'

beforeEach(async () => {
  vi.clearAllMocks()
  vi.resetModules()
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

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(10)),
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
