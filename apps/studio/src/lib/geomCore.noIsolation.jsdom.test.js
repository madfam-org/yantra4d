/**
 * geom-core 0.2.0 loads on a page that is NOT cross-origin isolated.
 *
 * 0.1.0 was a threaded build (shared WebAssembly memory + a pthread pool), so
 * the Studio refused to start it without COOP/COEP. 0.2.0's default `./wasm`
 * entry is single-threaded; this test runs the loader's real BROWSER branch
 * (`?url` asset import → `locateFile` → fetch of the `.wasm`) in jsdom with
 * `SharedArrayBuffer` deleted from the global, `crossOriginIsolated === false`
 * and `Worker` trapped, and then analyses a mesh with it.
 */
import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { MESH_FIXTURES, toBinarySTL } from './__fixtures__/meshFixtures'

const require = createRequire(import.meta.url)
const WASM_PATH = require.resolve('@madfam/geom-core/wasm-binary')

const saved = {}
const fetched = []
let workersStarted = 0
let sharedMemories = 0

beforeAll(() => {
  saved.SharedArrayBuffer = globalThis.SharedArrayBuffer
  saved.process = globalThis.process
  saved.fetch = globalThis.fetch
  saved.Memory = WebAssembly.Memory

  delete globalThis.SharedArrayBuffer
  vi.stubGlobal('crossOriginIsolated', false)
  vi.stubGlobal('Worker', class { constructor() { workersStarted++; throw new Error('geom-core must not start a Worker') } })
  WebAssembly.Memory = class extends saved.Memory {
    constructor(desc) { if (desc?.shared) sharedMemories++; super(desc) }
  }
  // Serve the package's own .wasm for the URL the loader asks for.
  vi.stubGlobal('fetch', async (url) => {
    fetched.push(String(url))
    if (!String(url).endsWith('.wasm')) return new Response('not found', { status: 404 })
    return new Response(readFileSync(WASM_PATH), { headers: { 'Content-Type': 'application/wasm' } })
  })
})

afterAll(() => {
  vi.unstubAllGlobals()
  globalThis.SharedArrayBuffer = saved.SharedArrayBuffer
  WebAssembly.Memory = saved.Memory
})

describe('geom-core 0.2.0 without cross-origin isolation (jsdom, browser branch)', () => {
  it('loads the WASM and analyses a mesh with SharedArrayBuffer absent', async () => {
    expect(typeof globalThis.SharedArrayBuffer).toBe('undefined')
    expect(globalThis.crossOriginIsolated).toBe(false)
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '1')
    vi.resetModules()
    const info = vi.spyOn(console, 'info').mockImplementation(() => {})
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})

    // Take the browser branch of the loader and of the Emscripten module:
    // both decide "Node or browser" from process.versions.node when they load.
    vi.stubGlobal('process', { ...saved.process, versions: { ...saved.process.versions, node: undefined } })
    let mod
    let browser
    try {
      browser = await import('./geomCoreBrowser')
      mod = await browser.loadGeomCore()
    } finally {
      vi.stubGlobal('process', saved.process)
    }

    expect(warn).not.toHaveBeenCalled()
    expect(info).toHaveBeenCalledTimes(1)
    expect(browser.getGeomCoreBrowserStatus()).toMatchObject({ enabled: true, state: 'ready', reason: null })
    // The .wasm came through locateFile (the `?url` asset), not from the file system.
    expect(fetched.filter((u) => u.endsWith('.wasm'))).toHaveLength(1)
    expect(workersStarted).toBe(0)
    expect(sharedMemories).toBe(0)

    const box = MESH_FIXTURES.find((f) => f.name.startsWith('box 1x2x3 offset'))
    const m = browser.analyzeSTLBytes(mod, new Uint8Array(toBinarySTL(box)))
    expect(m.faceCount).toBe(12)
    expect(m.volumeMm3).toBeCloseTo(6, 9)
    expect(m.bbox).toEqual({ min: [10, -5, 7], max: [11, -3, 10] })
    info.mockRestore()
    warn.mockRestore()
  })
})
