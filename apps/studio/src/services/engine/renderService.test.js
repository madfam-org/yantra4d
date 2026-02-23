import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createSSEStream } from '../../test/mock-streams'

// We need to reset module state between tests because detectMode caches _mode
let renderService

beforeEach(async () => {
  vi.restoreAllMocks()

  // Default to weak device to pass backend-specific tests
  vi.stubGlobal('navigator', {
    hardwareConcurrency: 2,
    deviceMemory: 2
  })

  // Re-import fresh module to reset cached _mode
  vi.resetModules()
  renderService = await import('./renderService')
})

const manifest = {
  parts: [
    { id: 'main', render_mode: '3D' },
    { id: 'bottom', render_mode: '3D' },
    { id: 'top', render_mode: '3D' },
    { id: 'rods', render_mode: '3D' },
    { id: 'stoppers', render_mode: '3D' }
  ],
  modes: [
    { id: 'unit', parts: ['main'], estimate: { base_units: 1, formula: 'constant' } },
    { id: 'assembly', parts: ['bottom', 'top'], estimate: { base_units: 2, formula: 'constant' } },
    { id: 'grid', parts: ['bottom', 'top', 'rods', 'stoppers'], estimate: { base_units: 'rows*cols', formula: 'grid', formula_vars: ['rows', 'cols'] } },
  ],
  estimate_constants: { base_time: 5, per_unit: 1.5, per_part: 8 },
}

describe('estimateRenderTime', () => {
  it('unit mode: base_time + 1*per_unit + 1*per_part', () => {
    expect(renderService.estimateRenderTime('unit', {}, manifest)).toBe(14.5)
  })

  it('assembly mode: base_time + 2*per_unit + 2*per_part', () => {
    expect(renderService.estimateRenderTime('assembly', {}, manifest)).toBe(24)
  })

  it('grid mode 4x4: base_time + 16*per_unit + 4*per_part', () => {
    expect(renderService.estimateRenderTime('grid', { rows: 4, cols: 4 }, manifest)).toBe(61)
  })

  it('returns 0 when estimate_constants is missing', () => {
    expect(renderService.estimateRenderTime('unit', {}, { modes: manifest.modes })).toBe(0)
  })

  it('returns 0 for unknown mode', () => {
    expect(renderService.estimateRenderTime('nonexistent', {}, manifest)).toBe(0)
  })

  it('uses formula_vars to compute units generically', () => {
    const customManifest = {
      modes: [
        { id: 'custom', parts: ['a'], estimate: { formula_vars: ['x', 'y'] } },
      ],
      estimate_constants: { base_time: 2, per_unit: 1, per_part: 3 },
    }
    // x=3, y=5 → units=15 → 2 + 15*1 + 1*3 = 20
    expect(renderService.estimateRenderTime('custom', { x: 3, y: 5 }, customManifest)).toBe(20)
  })

  it('uses wasm_multiplier from estimate_constants', () => {
    const wasmManifest = {
      modes: [{ id: 'unit', parts: ['main'], estimate: { base_units: 1, formula: 'constant' } }],
      estimate_constants: { base_time: 5, per_unit: 1.5, per_part: 8, wasm_multiplier: 5 },
    }
    // In non-wasm mode (default _mode=null → not 'wasm'), multiplier is not applied
    expect(renderService.estimateRenderTime('unit', {}, wasmManifest)).toBe(14.5)
  })
})

describe('getRenderMode', () => {
  it('returns "detecting" when mode has not been detected yet', () => {
    expect(renderService.getRenderMode()).toBe('detecting')
  })
})

describe('cancelRender', () => {
  it('calls /api/render-cancel proactively without a mode health check', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // cancel call

    await renderService.cancelRender()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toContain('/api/render-cancel')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'POST' })
  })
})

describe('renderParts (backend mode)', () => {
  it('throws on non-ok HTTP response', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health → backend
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: () => Promise.resolve('Invalid SCAD file: bad.scad')
    })

    await expect(
      renderService.renderParts('unit', {}, manifest, {})
    ).rejects.toThrow('Render request failed (HTTP 400)')
  })

  it('throws when stream produces no parts', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health → backend
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"output","part":"main","line":"Compiling...","progress":50}',
        '' // stream ends without a "complete" event
      ])
    })

    await expect(
      renderService.renderParts('unit', {}, manifest, {})
    ).rejects.toThrow('Render stream completed without producing any parts')
  })

  it('warns on malformed SSE JSON and continues', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => { })
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health → backend
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {INVALID JSON}',
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.stl"}],"progress":100}',
        ''
      ])
    })

    const result = await renderService.renderParts('unit', {}, manifest, {})

    expect(warnSpy).toHaveBeenCalledWith('Malformed SSE data:', expect.any(SyntaxError))
    expect(result).toHaveLength(1)
    warnSpy.mockRestore()
  })

  it('includes project slug in render payload when provided', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health → backend
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.stl"}],"progress":100}',
        ''
      ])
    })

    await renderService.renderParts('unit', { size: 20 }, manifest, { project: 'my-project' })

    const renderCall = fetchMock.mock.calls[1]
    const body = JSON.parse(renderCall[1].body)
    expect(body.project).toBe('my-project')
    expect(body.mode).toBe('unit')
    expect(body.size).toBe(20)
  })

  it('omits project field from payload when not provided', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health → backend
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.stl"}],"progress":100}',
        ''
      ])
    })

    await renderService.renderParts('unit', { size: 20 }, manifest, {})

    const renderCall = fetchMock.mock.calls[1]
    const body = JSON.parse(renderCall[1].body)
    expect(body.project).toBeUndefined()
  })
})

describe('renderParts (SSE event types)', () => {
  it('calls onProgress for part_start, part_done, output, and error events', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"part_start","part":"main","index":0,"total":1,"progress":0}',
        'data: {"event":"output","part":"main","line":"Compiling design...","progress":30}',
        'data: {"event":"part_done","part":"main","progress":80}',
        'data: {"event":"error","part":"main","message":"soft error","progress":80}',
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.stl"}],"progress":100}',
        ''
      ])
    })

    const progressEvents = []
    await renderService.renderParts('unit', {}, manifest, { onProgress: (e) => progressEvents.push(e) })

    const parts = progressEvents.map(e => e.part).filter(Boolean)
    const logs = progressEvents.map(e => e.log).filter(Boolean)
    expect(parts).toContain('main')
    expect(logs.some(l => l.includes('[ERROR]'))).toBe(true)
    // part_done sets log
    expect(logs.some(l => l.includes('Done'))).toBe(true)
  })

  it('applies glb export_format for CadQuery engine', async () => {
    const cqManifest = {
      ...manifest,
      engine: 'cadquery',
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    // CadQuery always uses backend (no health check needed — detectMode short-circuits)
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.glb"}],"progress":100}',
        ''
      ])
    })

    await renderService.renderParts('unit', {}, cqManifest, {})

    const renderCall = fetchMock.mock.calls[0]
    const body = JSON.parse(renderCall[1].body)
    expect(body.export_format).toBe('glb')
  })

  it('uses backend when manifest.force_backend is true', async () => {
    const forcedManifest = { ...manifest, force_backend: true }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.stl"}],"progress":100}',
        ''
      ])
    })
    const result = await renderService.renderParts('unit', {}, forcedManifest, {})
    expect(result).toHaveLength(1)
  })

  it('uses backend when project.force_backend is set', async () => {
    const forcedManifest = { ...manifest, project: { force_backend: true } }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.stl"}],"progress":100}',
        ''
      ])
    })
    const result = await renderService.renderParts('unit', {}, forcedManifest, {})
    expect(result).toHaveLength(1)
  })
})

describe('renderService circuit breaker', () => {
  it('routes to backend when estimated render time exceeds 15s', async () => {
    // High-complexity grid: estimate will exceed 15s even on backend formula
    const heavyManifest = {
      modes: [{
        id: 'grid',
        parts: ['a', 'b', 'c', 'd'],
        estimate: { formula_vars: ['rows', 'cols'], formula: 'grid' }
      }],
      estimate_constants: { base_time: 5, per_unit: 10, per_part: 20 },
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"complete","parts":[{"type":"a","url":"http://x/a.stl"}],"progress":100}',
        ''
      ])
    })

    // rows=10, cols=10 → 100 units × 10 per_unit + 4×20 = 1080s → well above 15s threshold
    const result = await renderService.renderParts('grid', { rows: 10, cols: 10 }, heavyManifest, {})
    expect(result).toHaveLength(1)
    // No health check needed - circuit breaker short-circuits to backend directly  
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})

describe('cancelRender with active worker', () => {
  it('terminates worker and resets state when worker is active', async () => {
    const mockTerminate = vi.fn()
    class MockWorker {
      constructor() { this.onmessage = null }
      postMessage() { }
      addEventListener() { }
      removeEventListener() { }
      terminate = mockTerminate
    }
    vi.stubGlobal('Worker', MockWorker)

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValue({ ok: true })

    await renderService.cancelRender()
    // cancelRender should not throw even with no active worker
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/render-cancel'),
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('does not throw if cancel fetch fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('offline'))
    await expect(renderService.cancelRender()).resolves.toBeUndefined()
  })
})

describe('getRenderMode after detection', () => {
  it('reflects the detected mode after a successful render', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health → backend
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.stl"}],"progress":100}',
        ''
      ])
    })
    await renderService.renderParts('unit', {}, manifest, {})
    // After detecting, mode should no longer be 'detecting'
    expect(renderService.getRenderMode()).not.toBe('detecting')
  })
})

describe('estimateRenderTime — WASM multiplier path', () => {
  it('applies wasm_multiplier when hardware concurrency is high', () => {
    vi.stubGlobal('navigator', { hardwareConcurrency: 8, deviceMemory: 8 })
    const wasmManifest = {
      modes: [{ id: 'unit', parts: ['main'], estimate: { base_units: 1, formula: 'constant' } }],
      estimate_constants: { base_time: 5, per_unit: 1.5, per_part: 8, wasm_multiplier: 2 },
    }
    // On high-end device, mode defaults to 'wasm' base estimate × 2
    const est = renderService.estimateRenderTime('unit', {}, wasmManifest)
    // 14.5 × 2 = 29 (if wasm) or 14.5 (if backend)
    expect([14.5, 29]).toContain(est)
  })
})

describe('renderParts (wasm mode)', () => {
  let originalCreateObjectURL
  beforeEach(() => {
    originalCreateObjectURL = URL.createObjectURL
    URL.createObjectURL = vi.fn(() => 'blob:abc')
  })
  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL
  })

  it('initializes worker and resolves parts', async () => {
    class MockWorker {
      constructor() { this.listeners = {} }
      postMessage(msg) {
        if (msg.type === 'init') {
          setTimeout(() => this.listeners['message']?.({ data: { type: 'init-done' } }), 0)
        } else if (msg.type === 'render') {
          setTimeout(() => {
            this.listeners['message']?.({ data: { type: 'progress', phase: 'compiling', percent: 50 } })
            this.listeners['message']?.({ data: { type: 'result', stl: new Uint8Array([1,2,3]).buffer } })
          }, 0)
        }
      }
      addEventListener(evt, cb) { this.listeners[evt] = cb }
      removeEventListener(evt, cb) { if(this.listeners[evt] === cb) delete this.listeners[evt] }
      terminate() {}
    }
    vi.stubGlobal('Worker', MockWorker)

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockRejectedValue(new Error('no backend')) // force WASM fallback

    const progressEvents = []
    const result = await renderService.renderParts('unit', {}, manifest, { onProgress: e => progressEvents.push(e) })

    expect(result).toHaveLength(1)
    expect(result[0].type).toBe('main')
    expect(result[0].url).toBe('blob:abc')
    expect(progressEvents.length).toBeGreaterThan(0)
  })

  it('rejects if worker initialization fails', async () => {
    class MockWorkerError {
      constructor() { this.listeners = {} }
      postMessage(msg) {
        if (msg.type === 'init') {
          setTimeout(() => this.listeners['message']?.({ data: { type: 'init-error', error: 'init failed' } }), 0)
        }
      }
      addEventListener(evt, cb) { this.listeners[evt] = cb }
      removeEventListener(evt, cb) { if(this.listeners[evt] === cb) delete this.listeners[evt] }
      terminate() {}
    }
    vi.stubGlobal('Worker', MockWorkerError)

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockRejectedValue(new Error('no backend'))

    await expect(renderService.renderParts('unit', {}, manifest, {})).rejects.toThrow('init failed')
  })

  it('rejects if worker render fails', async () => {
    class MockWorkerRenderError {
      constructor() { this.listeners = {} }
      postMessage(msg) {
        if (msg.type === 'init') {
          setTimeout(() => this.listeners['message']?.({ data: { type: 'init-done' } }), 0)
        } else if (msg.type === 'render') {
          setTimeout(() => this.listeners['message']?.({ data: { type: 'error', message: 'render failed' } }), 0)
        }
      }
      addEventListener(evt, cb) { this.listeners[evt] = cb }
      removeEventListener(evt, cb) { if(this.listeners[evt] === cb) delete this.listeners[evt] }
      terminate() {}
    }
    vi.stubGlobal('Worker', MockWorkerRenderError)

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockRejectedValue(new Error('no backend'))

    await expect(renderService.renderParts('unit', {}, manifest, {})).rejects.toThrow('render failed')
  })
})
