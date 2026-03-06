import { describe, it, expect, vi, beforeEach } from 'vitest'
import { YantraEngine } from '../engine'
import type { YantraCartridge, YantraManifest } from '../types'

function createTestCartridge(overrides: Partial<YantraManifest> = {}): YantraCartridge {
  return {
    manifest: {
      project: { name: 'Test', slug: 'test-project', version: '1.0.0' },
      parameters: [
        { id: 'width', type: 'slider', default: 10, min: 1, max: 100 },
        { id: 'height', type: 'slider', default: 20, min: 5, max: 50 },
        { id: 'quality', type: 'select', default: 'medium' },
      ],
      parts: [{ id: 'body', render_mode: 0 }],
      modes: [{ id: 'Standard', scad_file: 'main.scad', parts: ['body'] }],
      ...overrides,
    },
  }
}

describe('YantraEngine', () => {
  let engine: YantraEngine

  beforeEach(() => {
    engine = new YantraEngine({ apiBase: 'http://localhost:5000' })
    vi.restoreAllMocks()
  })

  describe('getDefaultParams', () => {
    it('extracts defaults from all parameters', () => {
      const cartridge = createTestCartridge()
      const params = engine.getDefaultParams(cartridge)
      expect(params).toEqual({ width: 10, height: 20, quality: 'medium' })
    })

    it('returns empty object for cartridge with no parameters', () => {
      const cartridge = createTestCartridge({ parameters: [] })
      expect(engine.getDefaultParams(cartridge)).toEqual({})
    })
  })

  describe('evaluateConstraints', () => {
    it('returns empty violations for valid params', () => {
      const cartridge = createTestCartridge()
      const violations = engine.evaluateConstraints(cartridge, { width: 50, height: 25 })
      expect(violations).toEqual({})
    })

    it('reports min violations', () => {
      const cartridge = createTestCartridge()
      const violations = engine.evaluateConstraints(cartridge, { width: 0, height: 25 })
      expect(violations.width).toContain('Value must be >= 1')
    })

    it('reports max violations', () => {
      const cartridge = createTestCartridge()
      const violations = engine.evaluateConstraints(cartridge, { width: 200, height: 25 })
      expect(violations.width).toContain('Value must be <= 100')
    })

    it('reports multiple violations on same parameter', () => {
      const cartridge = createTestCartridge()
      // height < min (5)
      const violations = engine.evaluateConstraints(cartridge, { width: 50, height: 0 })
      expect(violations.height).toHaveLength(1)
      expect(violations.height[0]).toContain('>= 5')
    })

    it('skips constraint checks for parameters without min/max', () => {
      const cartridge = createTestCartridge()
      const violations = engine.evaluateConstraints(cartridge, { width: 50, height: 25, quality: 'high' })
      expect(violations.quality).toBeUndefined()
    })
  })

  describe('render', () => {
    it('sends POST request with correct payload', async () => {
      globalThis.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ url: '/renders/abc123.glb', logs: 'done' }),
      })

      const cartridge = createTestCartridge()
      const result = await engine.render(cartridge, {
        mode: 'Standard',
        params: { width: 42 },
        parts: ['body'],
      })

      expect(globalThis.fetch).toHaveBeenCalledWith(
        'http://localhost:5000/api/projects/test-project/render',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            mode: 'Standard',
            params: { width: 42 },
            parts: ['body'],
            colors: {},
          }),
        })
      )

      expect(result.url).toBe('http://localhost:5000/renders/abc123.glb')
      expect(result.logs).toBe('done')
    })

    it('throws on render failure', async () => {
      globalThis.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.resolve({ error: 'OpenSCAD timeout' }),
      })

      const cartridge = createTestCartridge()
      await expect(
        engine.render(cartridge, { mode: 'Standard' })
      ).rejects.toThrow('Render failed (500): OpenSCAD timeout')
    })

    it('handles json parse failure in error response', async () => {
      globalThis.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 502,
        statusText: 'Bad Gateway',
        json: () => Promise.reject(new Error('not json')),
      })

      const cartridge = createTestCartridge()
      await expect(
        engine.render(cartridge, { mode: 'Standard' })
      ).rejects.toThrow('Render failed (502): Bad Gateway')
    })
  })
})
