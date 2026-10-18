import { describe, it, expect, vi, afterEach } from 'vitest'

async function freshModule() {
  vi.resetModules()
  return import('./geomCoreBrowser')
}

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  window.history.replaceState({}, '', '/')
})

describe('parseGeomCoreFlag', () => {
  it('accepts on/off spellings and ignores anything else', async () => {
    const { parseGeomCoreFlag } = await freshModule()
    for (const v of ['1', 'true', 'on', ' TRUE ']) expect(parseGeomCoreFlag(v)).toBe(true)
    for (const v of ['0', 'false', 'off']) expect(parseGeomCoreFlag(v)).toBe(false)
    for (const v of [undefined, null, '', 'yes', 'wasm']) expect(parseGeomCoreFlag(v)).toBeNull()
  })
})

describe('VITE_GEOM_CORE_BROWSER flag', () => {
  it('is off by default and reports state "off"', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '')
    const m = await freshModule()
    expect(m.isGeomCoreBrowserEnabled()).toBe(false)
    expect(m.getGeomCoreBrowserStatus()).toEqual({ enabled: false, state: 'off', version: '0.2.0', reason: null })
  })

  it('turns on from the build-time env', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '1')
    const m = await freshModule()
    expect(m.isGeomCoreBrowserEnabled()).toBe(true)
    expect(m.getGeomCoreBrowserStatus().state).toBe('idle')
  })

  it('?geomcore=1 turns it on per session without the env', async () => {
    window.history.replaceState({}, '', '/?geomcore=1')
    const m = await freshModule()
    expect(m.isGeomCoreBrowserEnabled()).toBe(true)
  })

  it('?geomcore=0 overrides an env pin', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '1')
    window.history.replaceState({}, '', '/?geomcore=0')
    const m = await freshModule()
    expect(m.isGeomCoreBrowserEnabled()).toBe(false)
  })
})

describe('loadGeomCore (0.2.0 single-threaded build)', () => {
  afterEach(() => {
    vi.doUnmock('@madfam/geom-core/wasm')
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('logs exactly one console.info line when geom-core becomes active', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '1')
    const m = await freshModule()
    const info = vi.spyOn(console, 'info').mockImplementation(() => {})
    const mod = await m.loadGeomCore()
    await m.loadGeomCore() // cached: no second line
    expect(typeof mod.Analyzer).toBe('function')
    expect(info).toHaveBeenCalledTimes(1)
    expect(info.mock.calls[0][0]).toBe('[geom-core] 0.2.0 WASM active (single-threaded); mesh metrics come from geom-core')
    expect(m.getGeomCoreBrowserStatus()).toMatchObject({ state: 'ready', reason: null })
  })

  it('gives up after 10 s on an initialisation that never settles', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '1')
    vi.doMock('@madfam/geom-core/wasm', () => ({ default: () => new Promise(() => {}) }))
    const m = await freshModule()
    await import('@madfam/geom-core/wasm') // resolve the mocked module before faking time
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    let settled = null
    m.loadGeomCore().then(() => { settled = 'resolved' }, (err) => { settled = err })
    for (let i = 0; i < 40 && settled === null; i++) await vi.advanceTimersByTimeAsync(500)
    expect(settled).toBeInstanceOf(Error)
    expect(settled.message).toBe('@madfam/geom-core 0.2.0 initialisation did not finish within 10000 ms')
    expect(warn).toHaveBeenCalledTimes(1)
    expect(m.getGeomCoreBrowserStatus()).toMatchObject({ state: 'failed', reason: settled.message })
  })
})

describe('reportGeomCoreFailure', () => {
  it('warns once, then records the latest reason in the status', async () => {
    vi.stubEnv('VITE_GEOM_CORE_BROWSER', '1')
    const m = await freshModule()
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    expect(m.reportGeomCoreFailure(new Error('first'))).toBe('first')
    m.reportGeomCoreFailure('second')
    expect(warn).toHaveBeenCalledTimes(1)
    expect(warn.mock.calls[0][0]).toMatch(/using the TypeScript path: first/)
    expect(m.getGeomCoreBrowserStatus()).toMatchObject({ enabled: true, state: 'failed', reason: 'second' })
    warn.mockRestore()
  })
})

describe('geometryToSTLBytes', () => {
  it('writes header count and float32 vertices for indexed geometry', async () => {
    const { geometryToSTLBytes } = await freshModule()
    const positions = [0, 0, 0, 10, 0, 0, 0, 10, 0]
    const geometry = {
      attributes: { position: { count: 3, getX: (i) => positions[i * 3], getY: (i) => positions[i * 3 + 1], getZ: (i) => positions[i * 3 + 2] } },
      index: { count: 3, getX: (i) => [2, 1, 0][i] },
    }
    const bytes = geometryToSTLBytes(geometry)
    const view = new DataView(bytes.buffer)
    expect(bytes.byteLength).toBe(84 + 50)
    expect(view.getUint32(80, true)).toBe(1)
    // first vertex of the triangle is index 2 → (0, 10, 0)
    expect([view.getFloat32(96, true), view.getFloat32(100, true), view.getFloat32(104, true)]).toEqual([0, 10, 0])
  })

  it('throws on a geometry without positions', async () => {
    const { geometryToSTLBytes } = await freshModule()
    expect(() => geometryToSTLBytes({ attributes: {}, index: null })).toThrow('no position attribute')
  })
})
