import { describe, it, expect } from 'vitest'
import { inferPreviewHint } from './previewHintInference'

const makeManifest = (parts = ['cup', 'baseplate']) => ({
  modes: [{ id: 'default', parts }],
})

describe('inferPreviewHint', () => {
  describe('explicit preview_hint', () => {
    it('returns the explicit hint when present', () => {
      const paramDef = {
        id: 'foo',
        type: 'slider',
        label: { en: 'Foo' },
        preview_hint: { type: 'axis_scale', axis: 'z', affected_parts: ['cup'] },
      }
      const result = inferPreviewHint(paramDef, makeManifest(), 'default')
      expect(result).toEqual({ type: 'axis_scale', axis: 'z', affected_parts: ['cup'] })
    })

    it('prefers explicit hint over inferred', () => {
      const paramDef = {
        id: 'width',
        type: 'slider',
        label: { en: 'Width' },
        preview_hint: { type: 'part_highlight', affected_parts: ['baseplate'] },
      }
      const result = inferPreviewHint(paramDef, makeManifest(), 'default')
      expect(result.type).toBe('part_highlight')
      expect(result.affected_parts).toEqual(['baseplate'])
    })
  })

  describe('slider axis inference from label', () => {
    it.each([
      ['Width (units)', 'x'],
      ['Width', 'x'],
      ['X offset', 'x'],
      ['Depth (mm)', 'y'],
      ['Length', 'y'],
      ['Y size', 'y'],
      ['Height (units)', 'z'],
      ['Height', 'z'],
      ['Z offset', 'z'],
      ['Diameter', 'radial'],
      ['Radius (mm)', 'radial'],
    ])('infers axis "%s" → %s', (label, expectedAxis) => {
      const paramDef = { id: 'test', type: 'slider', label: { en: label } }
      const result = inferPreviewHint(paramDef, makeManifest(), 'default')
      expect(result.type).toBe('axis_scale')
      expect(result.axis).toBe(expectedAxis)
      expect(result.affected_parts).toEqual(['cup', 'baseplate'])
    })

    it('falls back to part_highlight for non-dimensional sliders', () => {
      const paramDef = { id: 'quality', type: 'slider', label: { en: 'Quality ($fn)' } }
      const result = inferPreviewHint(paramDef, makeManifest(), 'default')
      expect(result.type).toBe('part_highlight')
    })
  })

  describe('checkbox', () => {
    it('returns toggle_highlight', () => {
      const paramDef = { id: 'magnets', type: 'checkbox', label: { en: 'Enable Magnets' } }
      const result = inferPreviewHint(paramDef, makeManifest(), 'default')
      expect(result.type).toBe('toggle_highlight')
      expect(result.affected_parts).toEqual(['cup', 'baseplate'])
    })
  })

  describe('select', () => {
    it('returns part_highlight', () => {
      const paramDef = { id: 'style', type: 'select', label: { en: 'Lid Style' } }
      const result = inferPreviewHint(paramDef, makeManifest(), 'default')
      expect(result.type).toBe('part_highlight')
    })
  })

  describe('unknown type', () => {
    it('returns none for unsupported types', () => {
      const paramDef = { id: 'color', type: 'color', label: { en: 'Color' } }
      const result = inferPreviewHint(paramDef, makeManifest(), 'default')
      expect(result.type).toBe('none')
    })
  })

  describe('mode-aware part resolution', () => {
    it('uses parts from the current mode', () => {
      const manifest = {
        modes: [
          { id: 'cup', parts: ['cup'] },
          { id: 'baseplate', parts: ['baseplate'] },
        ],
      }
      const paramDef = { id: 'w', type: 'slider', label: { en: 'Width' } }

      const resultCup = inferPreviewHint(paramDef, manifest, 'cup')
      expect(resultCup.affected_parts).toEqual(['cup'])

      const resultBp = inferPreviewHint(paramDef, manifest, 'baseplate')
      expect(resultBp.affected_parts).toEqual(['baseplate'])
    })

    it('returns empty parts when mode not found', () => {
      const paramDef = { id: 'w', type: 'slider', label: { en: 'Width' } }
      const result = inferPreviewHint(paramDef, makeManifest(), 'nonexistent')
      expect(result.affected_parts).toEqual([])
    })
  })

  describe('edge cases', () => {
    it('handles missing label', () => {
      const paramDef = { id: 'x', type: 'slider' }
      const result = inferPreviewHint(paramDef, makeManifest(), 'default')
      expect(result.type).toBe('part_highlight')
    })

    it('handles null manifest', () => {
      const paramDef = { id: 'w', type: 'slider', label: { en: 'Width' } }
      const result = inferPreviewHint(paramDef, null, 'default')
      expect(result.type).toBe('axis_scale')
      expect(result.axis).toBe('x')
      expect(result.affected_parts).toEqual([])
    })

    it('handles manifest with no modes', () => {
      const paramDef = { id: 'h', type: 'checkbox', label: { en: 'Toggle' } }
      const result = inferPreviewHint(paramDef, { modes: [] }, 'default')
      expect(result.affected_parts).toEqual([])
    })
  })
})
