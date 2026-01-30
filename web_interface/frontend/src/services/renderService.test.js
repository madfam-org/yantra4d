import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createSSEStream } from '../test/mock-streams'

// We need to reset module state between tests because detectMode caches _mode
let renderService

beforeEach(async () => {
  vi.restoreAllMocks()
  // Re-import fresh module to reset cached _mode
  vi.resetModules()
  renderService = await import('./renderService')
})

const manifest = {
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
  it('in backend mode, calls /api/render-cancel', async () => {
    // First, make detectMode resolve to 'backend'
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockResolvedValueOnce({ ok: true }) // health check → backend
    fetchMock.mockResolvedValueOnce({ ok: true }) // cancel call

    // Trigger detection by calling cancelRender (which calls detectMode internally)
    await renderService.cancelRender()

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[1][0]).toContain('/api/render-cancel')
    expect(fetchMock.mock.calls[1][1]).toEqual({ method: 'POST' })
  })

  it('in wasm mode, does not call fetch for cancel', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockRejectedValueOnce(new Error('unreachable')) // health check fails → wasm

    await renderService.cancelRender()

    // Only the health check fetch, no cancel fetch
    expect(fetchMock).toHaveBeenCalledTimes(1)
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
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
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
})
