import { describe, expect, it } from 'vitest'
import { evaluateSafeFormula } from './safeFormula'

describe('evaluateSafeFormula', () => {
  it('evaluates arithmetic and comparison expressions', () => {
    expect(evaluateSafeFormula('width_units * depth_units <= 24', {
      width_units: 4,
      depth_units: 6,
    })).toBe(true)
  })

  it('evaluates grouped boolean expressions', () => {
    expect(evaluateSafeFormula('(rows + cols) > 4 && enabled == 1', {
      rows: 2,
      cols: 3,
      enabled: 1,
    })).toBe(true)
  })

  it('evaluates manifest ternary quantity formulas', () => {
    expect(evaluateSafeFormula('(enable_magnets ? 4 : 0) + (bp_enable_magnets ? 4 * width_units * depth_units : 0)', {
      enable_magnets: true,
      bp_enable_magnets: true,
      width_units: 3,
      depth_units: 2,
    })).toBe(28)
  })

  it('rejects unsupported function calls', () => {
    expect(() => evaluateSafeFormula('constructor.constructor("return process")()', {})).toThrow()
  })

  it('rejects missing numeric parameters', () => {
    expect(() => evaluateSafeFormula('rows * cols', { rows: 2 })).toThrow()
  })
})
