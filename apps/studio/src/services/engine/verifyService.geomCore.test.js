/**
 * verifyService × geom-core flag. Uses the real stl-utils parser and the real
 * geom-core WASM (manifold-3d stays mocked, as in verifyService.test.js).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MESH_FIXTURES, toBinarySTL } from '../../lib/__fixtures__/meshFixtures'

vi.mock('../core/backendDetection', () => ({
  isBackendAvailable: vi.fn(() => Promise.resolve(false)),
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('manifold-3d', () => ({
  default: () => Promise.resolve({
    Manifold: class {
      status() { return 0 }
      getProperties() { return { volume: 6, surfaceArea: 22 } }
      delete() { }
    },
    Mesh: class { delete() { } },
  }),
}))

const BOX = MESH_FIXTURES.find((f) => f.name.startsWith('box 1x2x3 offset'))

function stubSTLFetch() {
  const buffer = toBinarySTL(BOX)
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, arrayBuffer: () => Promise.resolve(buffer) })
}

async function runVerify() {
  const { verify } = await import('./verifyService')
  return verify([{ type: 'main', url: 'http://x/main.stl' }], 'unit')
}

beforeEach(() => {
  vi.resetModules()
  stubSTLFetch()
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.restoreAllMocks()
  vi.doUnmock('../../lib/geomCoreBrowser')
})

describe('verify (client) with the geom-core flag', () => {
  it('flag OFF: output is byte-identical to main', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '')
    const result = await runVerify()
    expect(result.output).toBe([
      '',
      '--- Part: main ---',
      '  Faces: 12',
      '  Bounding box: 1.00 x 2.00 x 3.00 mm',
      '  Manifold: YES',
      '  Volume: 6.00 mm³',
      '  Surface area: 22.00 mm²',
    ].join('\n'))
    expect(result.passed).toBe(true)
  })

  it('flag ON: face count and bbox come from geom-core, and the output says so', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '1')
    const result = await runVerify()
    expect(result.output).toContain('  Geometry core: geom-core WASM\n  Faces: 12\n  Bounding box: 1.00 x 2.00 x 3.00 mm')
    expect(result.passed).toBe(true)
  })

  it('flag ON but WASM unavailable: TypeScript numbers, with the reason in the output', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '1')
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.doMock('../../lib/geomCoreBrowser', async (importOriginal) => ({
      ...(await importOriginal()),
      loadGeomCore: () => Promise.reject(new Error('page is not cross-origin isolated')),
    }))
    const result = await runVerify()
    expect(result.output).toContain('  Geometry core: TypeScript (geom-core unavailable: page is not cross-origin isolated)\n  Faces: 12\n  Bounding box: 1.00 x 2.00 x 3.00 mm')
    expect(result.passed).toBe(true)
    expect(warn).toHaveBeenCalledTimes(1)
  })
})
