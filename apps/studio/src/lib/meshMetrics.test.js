import { describe, it, expect, vi, afterEach } from 'vitest'
import * as printEstimator from './printEstimator'
import { MESH_FIXTURES, toBufferGeometry } from './__fixtures__/meshFixtures'

// Records whether anything imported the WASM package.
const wasmImports = vi.hoisted(() => ({ count: 0 }))
vi.mock('@madfam/geom-core/wasm', async (importOriginal) => {
  wasmImports.count++
  return importOriginal()
})

async function freshModules() {
  vi.resetModules()
  const meshMetrics = await import('./meshMetrics')
  const browser = await import('./geomCoreBrowser')
  return { meshMetrics, browser }
}

afterEach(() => {
  vi.unstubAllEnvs()
  wasmImports.count = 0
})

describe('flag OFF (default): identical to main', () => {
  it('every accessor returns exactly the printEstimator result, for every fixture', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '')
    const { meshMetrics } = await freshModules()
    for (const fixture of MESH_FIXTURES) {
      const g = toBufferGeometry(fixture)
      expect(Object.is(meshMetrics.meshVolumeMm3(g), printEstimator.computeVolumeMm3(g))).toBe(true)
      expect(meshMetrics.meshBoundingBox(g)).toStrictEqual(printEstimator.computeBoundingBox(g))
      expect(meshMetrics.meshCentroid(g)).toStrictEqual(printEstimator.computeCentroid(g))
    }
    // null / empty inputs keep main's sentinels
    expect(meshMetrics.meshVolumeMm3(null)).toBe(0)
    expect(meshMetrics.meshBoundingBox(null)).toStrictEqual({ width: 0, depth: 0, height: 0 })
    expect(meshMetrics.meshCentroid(null)).toStrictEqual({ x: 0, y: 0, z: 0 })
  })

  it('never loads the WASM: prefetch is a no-op and nothing imports the package', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '')
    const { meshMetrics, browser } = await freshModules()
    const g = toBufferGeometry(MESH_FIXTURES[3])
    await expect(meshMetrics.prefetchGeomCoreMetrics(g)).resolves.toBe(false)
    expect(meshMetrics.cachedGeomCoreMetrics(g)).toBeNull()
    expect(wasmImports.count).toBe(0)
    expect(browser.getGeomCoreBrowserStatus().state).toBe('off')
  })
})

describe('flag ON: accessors return the cached WASM metrics', () => {
  it('falls back to TypeScript until prefetch lands, then serves geom-core numbers', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '1')
    const { meshMetrics, browser } = await freshModules()
    const g = toBufferGeometry(MESH_FIXTURES[6]) // 1x2x3 box at (10,-5,7)
    expect(meshMetrics.cachedGeomCoreMetrics(g)).toBeNull()
    expect(meshMetrics.meshVolumeMm3(g)).toBe(printEstimator.computeVolumeMm3(g))

    await expect(meshMetrics.prefetchGeomCoreMetrics(g)).resolves.toBe(true)
    await expect(meshMetrics.prefetchGeomCoreMetrics(g)).resolves.toBe(false) // cached
    expect(wasmImports.count).toBe(1)
    expect(browser.getGeomCoreBrowserStatus().state).toBe('ready')

    const cached = meshMetrics.cachedGeomCoreMetrics(g)
    expect(meshMetrics.meshVolumeMm3(g)).toBe(cached.volumeMm3)
    expect(meshMetrics.meshBoundingBox(g)).toBe(cached.boundingBox)
    expect(meshMetrics.meshCentroid(g)).toBe(cached.centroid)
    expect(cached.volumeMm3).toBeCloseTo(6, 9)
    expect(cached.boundingBox).toEqual({ width: 1, depth: 2, height: 3 })
    expect(cached.centroid.x).toBeCloseTo(10.5, 9)
  })

  it('a failing WASM load is visible and leaves the TypeScript numbers in place', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '1')
    const { meshMetrics, browser } = await freshModules()
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const g = toBufferGeometry(MESH_FIXTURES[6])
    // A real failure: a browser page that is not cross-origin isolated. The
    // blocker is checked synchronously inside prefetch, so the stub only has
    // to cover the call itself.
    vi.stubGlobal('process', { ...globalThis.process, versions: { ...globalThis.process.versions, node: undefined } })
    vi.stubGlobal('crossOriginIsolated', false)
    let pending
    try {
      pending = meshMetrics.prefetchGeomCoreMetrics(g)
    } finally {
      vi.unstubAllGlobals()
    }
    await expect(pending).resolves.toBe(false)
    expect(warn).toHaveBeenCalledTimes(1)
    expect(warn.mock.calls[0][0]).toMatch(/not cross-origin isolated/)
    expect(browser.getGeomCoreBrowserStatus()).toMatchObject({ state: 'failed', reason: expect.stringMatching(/COOP\/COEP/) })
    expect(meshMetrics.cachedGeomCoreMetrics(g)).toBeNull()
    expect(meshMetrics.meshVolumeMm3(g)).toBe(printEstimator.computeVolumeMm3(g))
    expect(wasmImports.count).toBe(0)
    warn.mockRestore()
  })

  it('skips a geometry without positions without reporting a failure', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '1')
    const { meshMetrics, browser } = await freshModules()
    await expect(meshMetrics.prefetchGeomCoreMetrics({ attributes: {}, index: null })).resolves.toBe(false)
    await expect(meshMetrics.prefetchGeomCoreMetrics(null)).resolves.toBe(false)
    expect(browser.getGeomCoreBrowserStatus().state).toBe('idle')
  })
})
