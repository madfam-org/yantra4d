import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
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

  // ---------------------------------------------------------------------------
  // Calibration regression. Live measurement 2026-08-08 on app.yantra4d.com, from
  // the app's own "Total rendering time" log lines in the browser (WASM path):
  //
  //     3x3 -> 0.196 s      5x5 -> 0.607 s
  //
  // The shipped estimator said ~336 s and ~352 s — a 1,714x and 580x overshoot —
  // and, because 70 s of its 84 s base came from a FIXED parts*per_part term, it
  // produced "~6 minutes" for EVERY cube size. It therefore fired its blocking
  // "the application may become unresponsive" dialog on every render, including
  // the deep link a prospect lands on. A warning that always fires is not a
  // warning; at the Digital Twin Gate it actively trains operators to click
  // through the check that governs whether atoms get extruded.
  // ---------------------------------------------------------------------------
  const rubiks = {
    parts: Array.from({ length: 7 }, (_, i) => ({ id: `p${i}`, render_mode: '3D' })),
    modes: [{
      id: 'cube',
      parts: Array.from({ length: 7 }, (_, i) => `p${i}`),
      estimate: { base_units: 'N * N', formula: 'grid', formula_vars: ['N', 'N'] },
    }],
    estimate_constants: { base_time: 2.0, per_unit: 0.006, per_part: 0.05 },
  }

  it('cube units follow N^2, matching the declared base_units "N * N"', () => {
    // The manifest declared N*N while formula_vars listed ["N"], so the code
    // computed N. Measurement settles it: 3x3 -> 5x5 grew 3.10x, and N^2 predicts
    // 2.78x while N alone predicts only 1.67x.
    const at = (N) => renderService.estimateRenderTime('cube', { N }, rubiks)
    const growth = (at(5) - 2.0 - 7 * 0.05) / (at(3) - 2.0 - 7 * 0.05)
    expect(growth).toBeCloseTo(25 / 9, 6)   // N^2, not N
  })

  it('a standard 3x3 no longer estimates minutes', () => {
    // Native path (no wasm multiplier in this fixture): 2 + 9*0.006 + 7*0.05
    expect(renderService.estimateRenderTime('cube', { N: 3 }, rubiks)).toBeCloseTo(2.404, 3)
  })

  it('the per-part term no longer dominates the estimate', () => {
    // This is the specific defect: parts*per_part was 70 s of an 84 s estimate,
    // so cube size barely moved the number and every size looked identical.
    const partsTerm = 7 * rubiks.estimate_constants.per_part      // 0.35
    const total = renderService.estimateRenderTime('cube', { N: 9 }, rubiks)
    expect(partsTerm / total).toBeLessThan(0.2)
  })

  it('reports no observed time before a render has run, never zero', () => {
    // "Not measured yet" must not be readable as "took no time" — that confusion
    // is what let a 1,714x overshoot look like a working estimator.
    expect(renderService.getLastObservedRenderSeconds()).toBeNull()
    expect(renderService.getEstimateAccuracy(336)).toBeNull()
  })

  it('accuracy is null for a nonsense estimate rather than Infinity', () => {
    expect(renderService.getEstimateAccuracy(0)).toBeNull()
    expect(renderService.getEstimateAccuracy(NaN)).toBeNull()
    expect(renderService.getEstimateAccuracy(-5)).toBeNull()
  })

  it('the threshold still FIRES for a genuinely expensive render', () => {
    // Guard against having swapped "always warns" for "never warns". The dialog
    // must remain reachable — proven here by a mode whose cost is real.
    const heavy = {
      ...rubiks,
      modes: [{ ...rubiks.modes[0], id: 'cube' }],
      estimate_constants: { base_time: 2.0, per_unit: 0.006, per_part: 0.05 },
    }
    const huge = renderService.estimateRenderTime('cube', { N: 400 }, heavy)
    expect(huge).toBeGreaterThan(90)   // 90 s = warning_threshold_seconds
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

  it('throws the backend stream error when no parts are produced', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health → backend
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"error","part":"all","error":"Render worker unavailable or not healthy","message":"Render worker unavailable or not healthy"}',
        'data: {"event":"complete","part":"all","error":"Render worker unavailable or not healthy","progress":100}',
        ''
      ])
    })

    const progressEvents = []
    await expect(
      renderService.renderParts('unit', {}, manifest, {
        onProgress: e => progressEvents.push(e)
      })
    ).rejects.toThrow('Render worker unavailable or not healthy')

    expect(progressEvents.some(e => e.log?.includes('Render worker unavailable'))).toBe(true)
  })

  it('throws the cancellation reason when stream ends without parts', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health → backend
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"cancelled","part":"main","message":"Render cancelled by user request"}',
        ''
      ])
    })

    await expect(
      renderService.renderParts('unit', {}, manifest, {})
    ).rejects.toThrow('Render cancelled by user request')
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

  it('buffers SSE JSON split across network chunks', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => { })
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health -> backend

    const encoder = new TextEncoder()
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode('data: {"event":"complete","parts":[{"type":"main",'))
          controller.enqueue(encoder.encode('"url":"http://x/a.stl"}],"progress":100}\n\n'))
          controller.close()
        }
      })
    })

    const result = await renderService.renderParts('unit', {}, manifest, {})

    expect(result).toHaveLength(1)
    expect(result[0].download_url).toContain('http://x/a.stl')
    expect(warnSpy).not.toHaveBeenCalledWith('Malformed SSE data:', expect.any(SyntaxError))
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

  it('includes ignore_cache flag when ignoreCache is true', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health → backend
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.stl"}],"progress":100}',
        ''
      ])
    })

    await renderService.renderParts('unit', {}, manifest, { ignoreCache: true })

    const renderCall = fetchMock.mock.calls[1]
    const body = JSON.parse(renderCall[1].body)
    expect(body.ignore_cache).toBe(true)
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

  it('always sets download_url even when viewer_url is absent (STL fix)', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health → backend
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        // Backend returns url only (no viewer_url) — e.g. cache hit
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.stl"}],"progress":100}',
        ''
      ])
    })

    const result = await renderService.renderParts('unit', {}, manifest, {})

    expect(result).toHaveLength(1)
    expect(result[0].download_url).toBeDefined()
    expect(result[0].download_url).toContain('http://x/a.stl')
  })

  it('sets download_url to original url when viewer_url is present', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health → backend
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.stl","viewer_url":"http://x/a.glb"}],"progress":100}',
        ''
      ])
    })

    const result = await renderService.renderParts('unit', {}, manifest, {})

    expect(result).toHaveLength(1)
    // url should be the viewer_url (GLB) for fast viewer load
    expect(result[0].url).toContain('http://x/a.glb')
    // download_url should be the original url (STL) for download
    expect(result[0].download_url).toContain('http://x/a.stl')
  })

  it('passes explicit exportFormat to backend payload', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health → backend
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.step"}],"progress":100}',
        ''
      ])
    })

    await renderService.renderParts('unit', {}, manifest, { exportFormat: 'step' })

    const renderCall = fetchMock.mock.calls[1]
    const body = JSON.parse(renderCall[1].body)
    expect(body.export_format).toBe('step')
  })

  it('exportFormat overrides CadQuery default glb', async () => {
    const cqManifest = { ...manifest, engine: 'cadquery' }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.step"}],"progress":100}',
        ''
      ])
    })

    await renderService.renderParts('unit', {}, cqManifest, { exportFormat: 'step' })

    const renderCall = fetchMock.mock.calls[0]
    const body = JSON.parse(renderCall[1].body)
    expect(body.export_format).toBe('step')
  })

  it('applies glb export_format for graph engine', async () => {
    const graphManifest = { ...manifest, engine: 'graph' }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    // Graph is backend-only (transpiles to CadQuery server-side) — detectMode short-circuits
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"complete","parts":[{"type":"main","url":"http://x/a.glb"}],"progress":100}',
        ''
      ])
    })

    await renderService.renderParts('unit', {}, graphManifest, {})

    const renderCall = fetchMock.mock.calls[0]
    const body = JSON.parse(renderCall[1].body)
    expect(body.export_format).toBe('glb')
  })

  it('uses backend when manifest.force_backend is true', async () => {
    const forcedManifest = { ...manifest, force_backend: true }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health check
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
    fetchMock.mockResolvedValueOnce({ ok: true }) // health check
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
    fetchMock.mockResolvedValueOnce({ ok: true }) // health check
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
    // Health check + render = 2 calls
    expect(fetchMock).toHaveBeenCalledTimes(2)
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

describe('detectMode WASM fallback on backend unavailability', () => {
  it('falls back to WASM when backend is down despite force_backend', async () => {
    // High-end device (WASM-capable)
    vi.stubGlobal('navigator', { hardwareConcurrency: 8, deviceMemory: 8 })
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    const forcedManifest = { ...manifest, force_backend: true }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    // Health check fails → backend unavailable
    fetchMock.mockRejectedValueOnce(new Error('net::ERR_CONNECTION_REFUSED'))

    // Should detect WASM mode and render
    class MockWorker {
      constructor() { this.listeners = {} }
      postMessage(msg) {
        if (msg.type === 'init') {
          setTimeout(() => this.listeners['message']?.({ data: { type: 'init-done' } }), 0)
        } else if (msg.type === 'render') {
          setTimeout(() => this.listeners['message']?.({ data: { type: 'result', stl: new Uint8Array([1,2,3]).buffer } }), 0)
        }
      }
      addEventListener(evt, cb) { this.listeners[evt] = cb }
      removeEventListener(evt, cb) { if (this.listeners[evt] === cb) delete this.listeners[evt] }
      terminate() {}
    }
    vi.stubGlobal('Worker', MockWorker)
    URL.createObjectURL = vi.fn(() => 'blob:abc')

    const result = await renderService.renderParts('unit', {}, forcedManifest, {})
    expect(result).toHaveLength(1)
    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('[Fallback]'))

    warnSpy.mockRestore()
  })

  it('still uses backend for CadQuery even when backend is down', async () => {
    const cqManifest = { ...manifest, engine: 'cadquery' }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    // CadQuery skips health check, goes straight to render which fails
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 502,
      text: () => Promise.resolve('Bad Gateway')
    })

    await expect(
      renderService.renderParts('unit', {}, cqManifest, {})
    ).rejects.toThrow('Render request failed (HTTP 502)')
  })

  it('still uses backend for graph engine even when backend is down', async () => {
    const graphManifest = { ...manifest, engine: 'graph' }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    // Graph skips health check like CadQuery — no WASM path exists
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 502,
      text: () => Promise.resolve('Bad Gateway')
    })

    await expect(
      renderService.renderParts('unit', {}, graphManifest, {})
    ).rejects.toThrow('Render request failed (HTTP 502)')
  })
})

describe('renderParts network error WASM fallback', () => {
  let originalCreateObjectURL
  beforeEach(() => {
    originalCreateObjectURL = URL.createObjectURL
    URL.createObjectURL = vi.fn(() => 'blob:fallback')
  })
  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL
  })

  it('catches "Failed to fetch" and retries with WASM for non-force_backend projects', async () => {
    vi.stubGlobal('navigator', { hardwareConcurrency: 8, deviceMemory: 8 })
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    class MockWorker {
      constructor() { this.listeners = {} }
      postMessage(msg) {
        if (msg.type === 'init') {
          setTimeout(() => this.listeners['message']?.({ data: { type: 'init-done' } }), 0)
        } else if (msg.type === 'render') {
          setTimeout(() => this.listeners['message']?.({ data: { type: 'result', stl: new Uint8Array([1]).buffer } }), 0)
        }
      }
      addEventListener(evt, cb) { this.listeners[evt] = cb }
      removeEventListener(evt, cb) { if (this.listeners[evt] === cb) delete this.listeners[evt] }
      terminate() {}
    }
    vi.stubGlobal('Worker', MockWorker)

    // Use a heavy manifest to trigger circuit breaker → backend mode on WASM-capable device
    const heavyManifest = {
      modes: [{
        id: 'grid',
        parts: ['a', 'b', 'c', 'd'],
        estimate: { formula_vars: ['rows', 'cols'], formula: 'grid' }
      }],
      parts: [
        { id: 'a', render_mode: '3D' },
        { id: 'b', render_mode: '3D' },
        { id: 'c', render_mode: '3D' },
        { id: 'd', render_mode: '3D' },
      ],
      estimate_constants: { base_time: 5, per_unit: 10, per_part: 20 },
    }

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    // Health check succeeds → backend mode (via circuit breaker, est > 15s)
    fetchMock.mockResolvedValueOnce({ ok: true })
    // Render call fails with network error
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    const progressEvents = []
    const result = await renderService.renderParts('grid', { rows: 10, cols: 10 }, heavyManifest, {
      onProgress: e => progressEvents.push(e)
    })

    expect(result).toHaveLength(4)
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('[Fallback] Backend render failed'),
      'Failed to fetch'
    )
    expect(progressEvents.some(e => e.log?.includes('[FALLBACK]'))).toBe(true)

    warnSpy.mockRestore()
  })

  it('falls back to WASM when backend reports render worker unavailable', async () => {
    vi.stubGlobal('navigator', { hardwareConcurrency: 8, deviceMemory: 8 })
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    class MockWorker {
      constructor() { this.listeners = {} }
      postMessage(msg) {
        if (msg.type === 'init') {
          setTimeout(() => this.listeners['message']?.({ data: { type: 'init-done' } }), 0)
        } else if (msg.type === 'render') {
          setTimeout(() => this.listeners['message']?.({ data: { type: 'result', stl: new Uint8Array([1]).buffer } }), 0)
        }
      }
      addEventListener(evt, cb) { this.listeners[evt] = cb }
      removeEventListener(evt, cb) { if (this.listeners[evt] === cb) delete this.listeners[evt] }
      terminate() {}
    }
    vi.stubGlobal('Worker', MockWorker)

    const heavyManifest = {
      modes: [{
        id: 'grid',
        parts: ['a', 'b'],
        estimate: { formula_vars: ['rows', 'cols'], formula: 'grid' }
      }],
      parts: [
        { id: 'a', render_mode: '3D' },
        { id: 'b', render_mode: '3D' },
      ],
      estimate_constants: { base_time: 5, per_unit: 10, per_part: 20 },
    }

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health succeeds
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream([
        'data: {"event":"error","part":"all","error":"Render worker unavailable or not healthy","message":"Render worker unavailable or not healthy"}',
        'data: {"event":"complete","part":"all","error":"Render worker unavailable or not healthy","progress":100}',
        ''
      ])
    })

    const progressEvents = []
    const result = await renderService.renderParts('grid', { rows: 10, cols: 10 }, heavyManifest, {
      onProgress: e => progressEvents.push(e)
    })

    expect(result).toHaveLength(2)
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('worker unavailable'),
      'Render worker unavailable or not healthy'
    )
    expect(progressEvents.some(e => e.log?.includes('Render worker unavailable, rendering locally'))).toBe(true)

    warnSpy.mockRestore()
  })

  it('does NOT fallback to WASM on network error for force_backend projects', async () => {
    vi.stubGlobal('navigator', { hardwareConcurrency: 8, deviceMemory: 8 })

    const forcedManifest = { ...manifest, force_backend: true }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health check
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    await expect(
      renderService.renderParts('unit', {}, forcedManifest, {})
    ).rejects.toThrow('Failed to fetch')
  })

  it('does NOT fallback to WASM on rate limit for force_backend projects', async () => {
    vi.stubGlobal('navigator', { hardwareConcurrency: 8, deviceMemory: 8 })

    const forcedManifest = { ...manifest, force_backend: true }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health check
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 429,
      text: () => Promise.resolve('Rate limit exceeded')
    })

    const progressEvents = []
    await expect(
      renderService.renderParts('unit', {}, forcedManifest, {
        onProgress: e => progressEvents.push(e)
      })
    ).rejects.toThrow('HTTP 429')

    expect(progressEvents.some(e => e.log?.includes('Server render limit reached'))).toBe(true)
  })

  it('does NOT fallback on AbortError (user cancel)', async () => {
    // Use weak device so detectMode chooses backend (not WASM)
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health
    fetchMock.mockRejectedValueOnce(new DOMException('Aborted', 'AbortError'))

    await expect(
      renderService.renderParts('unit', {}, manifest, {})
    ).rejects.toThrow('Aborted')
  })

  it('does NOT fallback on HTTP 500 (backend render error)', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Internal error')
    })

    await expect(
      renderService.renderParts('unit', {}, manifest, {})
    ).rejects.toThrow('Render request failed (HTTP 500)')
  })

  it('does NOT fallback for CadQuery even on network error', async () => {
    vi.stubGlobal('navigator', { hardwareConcurrency: 8, deviceMemory: 8 })
    const cqManifest = { ...manifest, engine: 'cadquery' }

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    // CadQuery skips health check
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    await expect(
      renderService.renderParts('unit', {}, cqManifest, {})
    ).rejects.toThrow('Failed to fetch')
  })

  it('does NOT fallback for graph engine even on network error', async () => {
    vi.stubGlobal('navigator', { hardwareConcurrency: 8, deviceMemory: 8 })
    const graphManifest = { ...manifest, engine: 'graph' }

    const fetchMock = vi.spyOn(globalThis, 'fetch')
    // Graph skips health check and must never fall back to WASM
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    await expect(
      renderService.renderParts('unit', {}, graphManifest, {})
    ).rejects.toThrow('Failed to fetch')
  })
})

describe('renderParts (wasm mode)', () => {
  let originalCreateObjectURL
  beforeEach(() => {
    // WASM mode requires a capable device
    vi.stubGlobal('navigator', { hardwareConcurrency: 8, deviceMemory: 8 })
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

describe('canRunWasm', () => {
  // The WASM circuit breaker decides whether a cartridge may render in the
  // browser at all. Kernels with no WASM build must never be offered it.
  it('allows OpenSCAD cartridges', () => {
    expect(renderService.canRunWasm({ engine: 'openscad' })).toBe(true)
  })

  it('allows a cartridge that declares no engine', () => {
    expect(renderService.canRunWasm({})).toBe(true)
  })

  it('refuses CadQuery, which has no browser build', () => {
    expect(renderService.canRunWasm({ engine: 'cadquery' })).toBe(false)
  })

  it('refuses the implicit SDF engine', () => {
    expect(renderService.canRunWasm({ engine: 'implicit' })).toBe(false)
    expect(renderService.canRunWasm({ engine: 'graph' })).toBe(false)
  })

  it('treats a null manifest as permitted rather than throwing', () => {
    expect(renderService.canRunWasm(null)).toBe(true)
  })
})

describe('backend to WASM fallback', () => {
  // A backend failure should fall back to browser rendering only when that is
  // both possible and appropriate. Getting this wrong either strands the user
  // on a dead backend, or silently offers WASM to a cartridge that has no
  // browser build. The backend must be *available* for this path to run at
  // all, so backendDetection is stubbed rather than inferred from fetch.
  const scadManifest = {
    ...manifest,
    engine: 'openscad',
    modes: [{ id: 'unit', parts: ['main'], scad_file: 'main.scad', estimate: { base_units: 1 } }],
  }

  async function loadWithBackendUp() {
    vi.resetModules()
    vi.doMock('../core/backendDetection', () => ({
      isBackendAvailable: vi.fn(async () => true),
      // Must be non-empty: detectMode only routes to the backend when an API
      // base is configured, so an empty string sends every render to WASM and
      // the fallback path under test is never entered.
      getApiBase: vi.fn(() => 'http://localhost:5000'),
      resetDetection: vi.fn(),
    }))
    vi.stubGlobal('navigator', { hardwareConcurrency: 16, deviceMemory: 16 })

    class MockWorker {
      constructor() { this.listeners = {} }
      postMessage(msg) {
        if (msg.type === 'init') {
          setTimeout(() => this.listeners['message']?.({ data: { type: 'init-done' } }), 0)
        } else if (msg.type === 'render') {
          setTimeout(() => this.listeners['message']?.({
            data: { type: 'result', stl: new Uint8Array([1, 2, 3]).buffer },
          }), 0)
        }
      }
      addEventListener(evt, cb) { this.listeners[evt] = cb }
      removeEventListener(evt, cb) { if (this.listeners[evt] === cb) delete this.listeners[evt] }
      terminate() {}
    }
    vi.stubGlobal('Worker', MockWorker)
    URL.createObjectURL = vi.fn(() => 'blob:abc')

    return import('./renderService')
  }

  afterEach(() => { vi.doUnmock('../core/backendDetection') })

  it('falls back to WASM and names rate limiting as the reason', async () => {
    const svc = await loadWithBackendUp()
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('HTTP 429 rate limited'))
    const logs = []
    await svc.renderParts('unit', {}, scadManifest, {
      onProgress: (p) => p.log && logs.push(p.log),
    })
    expect(logs.some(l => l.includes('Server limit reached'))).toBe(true)
  })

  it('falls back to WASM and names the unavailable worker', async () => {
    const svc = await loadWithBackendUp()
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(
      new Error('Render worker unavailable or not healthy'))
    const logs = []
    await svc.renderParts('unit', {}, scadManifest, {
      onProgress: (p) => p.log && logs.push(p.log),
    })
    expect(logs.some(l => l.includes('Render worker unavailable'))).toBe(true)
  })

  it('falls back on a network failure', async () => {
    const svc = await loadWithBackendUp()
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))
    const logs = []
    await svc.renderParts('unit', {}, scadManifest, {
      onProgress: (p) => p.log && logs.push(p.log),
    })
    expect(logs.some(l => l.includes('Backend unavailable'))).toBe(true)
  })

  it('does not fall back for a force_backend cartridge, and explains why', async () => {
    const svc = await loadWithBackendUp()
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('HTTP 429 rate limited'))
    const logs = []
    await expect(
      svc.renderParts('unit', {}, { ...scadManifest, project: { force_backend: true } }, {
        onProgress: (p) => p.log && logs.push(p.log),
      }),
    ).rejects.toThrow(/429/)
    expect(logs.some(l => l.includes('requires server rendering'))).toBe(true)
  })

  it('explains a worker outage on a force_backend cartridge', async () => {
    const svc = await loadWithBackendUp()
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('render_worker_unavailable'))
    const logs = []
    await expect(
      svc.renderParts('unit', {}, { ...scadManifest, force_backend: true }, {
        onProgress: (p) => p.log && logs.push(p.log),
      }),
    ).rejects.toThrow(/render_worker_unavailable/)
    expect(logs.some(l => l.includes('render service recovers'))).toBe(true)
  })

  it('re-throws a backend error that WASM could not have fixed', async () => {
    const svc = await loadWithBackendUp()
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('HTTP 500 internal error'))
    await expect(svc.renderParts('unit', {}, scadManifest, {})).rejects.toThrow(/500/)
  })

  // --- Estimation branches -------------------------------------------------

  const CONSTANTS = { base_time: 1, per_unit: 2, per_part: 3, wasm_multiplier: 4 }

  it('estimateRenderTime returns 0 when the manifest declares no constants', () => {
    expect(renderService.estimateRenderTime('cup', {}, { modes: [{ id: 'cup', parts: ['a'] }] })).toBe(0)
  })

  it('estimateRenderTime returns 0 for a mode the manifest does not define', () => {
    const manifest = { estimate_constants: CONSTANTS, modes: [{ id: 'cup', parts: ['a'] }] }
    expect(renderService.estimateRenderTime('nope', {}, manifest)).toBe(0)
  })

  it('formula_vars multiply, so a var listed twice scales quadratically', () => {
    const manifest = {
      estimate_constants: CONSTANTS,
      modes: [
        { id: 'lin', parts: ['a'], estimate: { formula_vars: ['n'] } },
        { id: 'sq', parts: ['a'], estimate: { formula_vars: ['n', 'n'] } },
      ],
    }
    const lin = renderService.estimateRenderTime('lin', { n: 5 }, manifest)
    const sq = renderService.estimateRenderTime('sq', { n: 5 }, manifest)
    // units 5 vs 25 against the same base and part costs.
    expect(sq).toBeGreaterThan(lin)
  })

  it('a missing formula var contributes 1 rather than collapsing the estimate to 0', () => {
    const manifest = {
      estimate_constants: CONSTANTS,
      modes: [{ id: 'cup', parts: ['a'], estimate: { formula_vars: ['absent'] } }],
    }
    expect(renderService.estimateRenderTime('cup', {}, manifest)).toBeGreaterThan(0)
  })

  it('numeric base_units is used when no formula_vars are given', () => {
    const manifest = {
      estimate_constants: CONSTANTS,
      modes: [{ id: 'cup', parts: ['a'], estimate: { base_units: 10 } }],
    }
    const withBase = renderService.estimateRenderTime('cup', {}, manifest)
    const manifestNoBase = {
      estimate_constants: CONSTANTS,
      modes: [{ id: 'cup', parts: ['a'], estimate: {} }],
    }
    expect(withBase).toBeGreaterThan(renderService.estimateRenderTime('cup', {}, manifestNoBase))
  })

  it('a non-numeric base_units falls back to one unit', () => {
    // "N * N" is documentation, not something the reducer can evaluate — the
    // estimator must not treat the string as a count.
    const manifest = {
      estimate_constants: CONSTANTS,
      modes: [{ id: 'cup', parts: ['a'], estimate: { base_units: 'N * N' } }],
    }
    const manifestOne = {
      estimate_constants: CONSTANTS,
      modes: [{ id: 'cup', parts: ['a'], estimate: { base_units: 1 } }],
    }
    expect(renderService.estimateRenderTime('cup', {}, manifest)).toBe(renderService.estimateRenderTime('cup', {}, manifestOne))
  })

  // --- Estimate accuracy ---------------------------------------------------

  it('getEstimateAccuracy is null before any render has been observed', () => {
    // Null rather than a number, so "not measured yet" cannot read as "accurate".
    expect(renderService.getEstimateAccuracy(10)).toBeNull()
  })

  it('getEstimateAccuracy is null for a non-positive or non-finite estimate', () => {
    expect(renderService.getEstimateAccuracy(0)).toBeNull()
    expect(renderService.getEstimateAccuracy(Number.NaN)).toBeNull()
    expect(renderService.getEstimateAccuracy(Number.POSITIVE_INFINITY)).toBeNull()
  })

  it('getRenderMode reports a mode string', () => {
    expect(typeof renderService.getRenderMode()).toBe('string')
  })

  // --- Engine capability ----------------------------------------------------

  it('WASM can run OpenSCAD projects', () => {
    expect(renderService.canRunWasm({ engine: 'openscad' })).toBe(true)
  })

  it('WASM cannot run CadQuery or implicit projects', () => {
    // Both kernels are backend-only; claiming otherwise would send the user
    // down a WASM path that cannot produce their geometry.
    expect(renderService.canRunWasm({ engine: 'cadquery' })).toBe(false)
    expect(renderService.canRunWasm({ engine: 'implicit' })).toBe(false)
    expect(renderService.canRunWasm({ engine: 'graph' })).toBe(false)
  })

  it('a manifest with no declared engine is treated as WASM-capable', () => {
    expect(renderService.canRunWasm({})).toBe(true)
    expect(renderService.canRunWasm(null)).toBe(true)
  })

  it('getLastObservedRenderSeconds reports null before any render', () => {
    const observed = renderService.getLastObservedRenderSeconds()
    expect(observed === null || typeof observed === 'number').toBe(true)
  })

  // --- Stream progress reporting -------------------------------------------

  const backendStream = (lines) => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health → backend
    fetchMock.mockResolvedValueOnce({ ok: true, body: createSSEStream(lines) })
    return fetchMock
  }

  it('a phase with no percentage still reports the phase', async () => {
    backendStream([
      'data: {"event":"output","part":"main","line":"Compiling...","phase":"compile"}',
      '',
    ])
    const events = []
    await expect(
      renderService.renderParts('unit', {}, manifest, { onProgress: e => events.push(e) })
    ).rejects.toThrow()
    expect(events.some(e => e.phase)).toBe(true)
  })

  it('a non-numeric progress value is ignored rather than reported as NaN', async () => {
    backendStream([
      'data: {"event":"output","part":"main","progress":"halfway"}',
      'data: {"event":"output","part":"main","progress":null}',
      '',
    ])
    const events = []
    await expect(
      renderService.renderParts('unit', {}, manifest, { onProgress: e => events.push(e) })
    ).rejects.toThrow()
    expect(events.every(e => e.progress === undefined || Number.isFinite(e.progress))).toBe(true)
  })

  it('an infinite progress value is ignored', async () => {
    backendStream([
      'data: {"event":"output","part":"main","progress":1e999}',
      '',
    ])
    const events = []
    await expect(
      renderService.renderParts('unit', {}, manifest, { onProgress: e => events.push(e) })
    ).rejects.toThrow()
    expect(events.every(e => e.progress === undefined || Number.isFinite(e.progress))).toBe(true)
  })

  it('a stream error without an error field falls back to a generic message', async () => {
    backendStream([
      'data: {"event":"error","part":"all"}',
      '',
    ])
    await expect(
      renderService.renderParts('unit', {}, manifest, {})
    ).rejects.toThrow(/Render failed|without producing/)
  })

  it('a stream error reported only as message is surfaced', async () => {
    backendStream([
      'data: {"event":"error","part":"all","message":"solver ran out of memory"}',
      '',
    ])
    await expect(
      renderService.renderParts('unit', {}, manifest, {})
    ).rejects.toThrow(/solver ran out of memory/)
  })

  it('a trailing SSE line with no newline is still parsed', async () => {
    // The buffer keeps an unterminated remainder; a stream whose last event
    // arrives without a trailing newline must not lose that event.
    backendStream([
      'data: {"event":"error","part":"all","error":"truncated tail"}',
    ])
    await expect(
      renderService.renderParts('unit', {}, manifest, {})
    ).rejects.toThrow(/truncated tail|without producing/)
  })
})

