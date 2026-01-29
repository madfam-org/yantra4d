import { describe, it, expect } from 'vitest'
import { estimateRenderTime } from './renderService'

const manifest = {
  modes: [
    { id: 'unit', parts: ['main'], estimate: { base_units: 1, formula: 'constant' } },
    { id: 'assembly', parts: ['bottom', 'top'], estimate: { base_units: 2, formula: 'constant' } },
    { id: 'grid', parts: ['bottom', 'top', 'rods', 'stoppers'], estimate: { formula: 'grid' } },
  ],
  estimate_constants: { base_time: 5, per_unit: 1.5, per_part: 8 },
}

describe('estimateRenderTime', () => {
  it('unit mode: base_time + 1*per_unit + 1*per_part', () => {
    // 5 + 1*1.5 + 1*8 = 14.5
    expect(estimateRenderTime('unit', {}, manifest)).toBe(14.5)
  })

  it('assembly mode: base_time + 2*per_unit + 2*per_part', () => {
    // 5 + 2*1.5 + 2*8 = 24
    expect(estimateRenderTime('assembly', {}, manifest)).toBe(24)
  })

  it('grid mode 4x4: base_time + 16*per_unit + 4*per_part', () => {
    // 5 + 16*1.5 + 4*8 = 5 + 24 + 32 = 61
    expect(estimateRenderTime('grid', { rows: 4, cols: 4 }, manifest)).toBe(61)
  })

  it('returns 0 when estimate_constants is missing', () => {
    expect(estimateRenderTime('unit', {}, { modes: manifest.modes })).toBe(0)
  })

  it('returns 0 for unknown mode', () => {
    expect(estimateRenderTime('nonexistent', {}, manifest)).toBe(0)
  })
})
