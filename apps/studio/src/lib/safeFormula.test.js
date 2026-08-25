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

  describe('operators', () => {
    it.each([
      ['1 + 2', 3],
      ['5 - 8', -3],
      ['3 * 4', 12],
      ['9 / 2', 4.5],
      ['7 % 3', 1],
      ['2 < 3', true],
      ['3 <= 3', true],
      ['4 > 5', false],
      ['5 >= 5', true],
      ['2 == 2', true],
      ['2 === 2', true],
      ['2 != 3', true],
      ['2 !== 3', true],
      ['1 && 0', false],
      ['0 || 3', true],
      ['!0', true],
      ['-4 + 10', 6],
      ['+3', 3],
      ['!!1', true],
    ])('evaluates %s', (formula, expected) => {
      expect(evaluateSafeFormula(formula, {})).toBe(expected)
    })

    it('respects precedence without parentheses', () => {
      expect(evaluateSafeFormula('2 + 3 * 4', {})).toBe(14)
    })

    it('parses decimals with and without a leading digit', () => {
      expect(evaluateSafeFormula('0.5 + .25', {})).toBe(0.75)
    })

    it('nests ternaries', () => {
      expect(evaluateSafeFormula('a > 2 ? (a > 4 ? 3 : 2) : 1', { a: 5 })).toBe(3)
      expect(evaluateSafeFormula('a > 2 ? (a > 4 ? 3 : 2) : 1', { a: 3 })).toBe(2)
      expect(evaluateSafeFormula('a > 2 ? (a > 4 ? 3 : 2) : 1', { a: 1 })).toBe(1)
    })
  })

  describe('parameter coercion', () => {
    it('accepts booleans', () => {
      expect(evaluateSafeFormula('flag ? 1 : 0', { flag: true })).toBe(1)
    })

    it('accepts numeric strings', () => {
      expect(evaluateSafeFormula('n + 1', { n: '41' })).toBe(42)
    })

    it('rejects a non-numeric string', () => {
      expect(() => evaluateSafeFormula('n + 1', { n: 'wide' })).toThrow(/Missing numeric parameter/)
    })

    it('rejects a blank string', () => {
      expect(() => evaluateSafeFormula('n + 1', { n: '   ' })).toThrow(/Missing numeric parameter/)
    })

    it('rejects null and undefined', () => {
      expect(() => evaluateSafeFormula('n', { n: null })).toThrow()
      expect(() => evaluateSafeFormula('n', {})).toThrow()
    })
  })

  describe('rejects malformed input', () => {
    // This parser exists so manifest formulas never reach eval(). Every one of
    // these has to fail closed rather than resolve to something surprising.
    it.each([
      ['unbalanced parenthesis', '(1 + 2'],
      ['trailing token', '1 + 2 3'],
      ['empty formula', ''],
      ['dangling operator', '1 +'],
      ['ternary without a colon', 'a ? 1', { a: 1 }],
      ['unsupported character', '1 # 2'],
      ['bare closing parenthesis', ')'],
    ])('%s', (_name, formula, params = {}) => {
      expect(() => evaluateSafeFormula(formula, params)).toThrow()
    })

    it('division by zero', () => {
      expect(() => evaluateSafeFormula('1 / 0', {})).toThrow(/Division by zero/)
    })

    it('modulo by zero', () => {
      expect(() => evaluateSafeFormula('1 % 0', {})).toThrow(/Division by zero/)
    })

    it('a formula longer than the limit', () => {
      expect(() => evaluateSafeFormula('1 +'.repeat(200) + '1', {})).toThrow(/too long/)
    })

    it('a formula with more tokens than the limit', () => {
      // Under the 256-char cap but over the 128-token cap.
      expect(() => evaluateSafeFormula('1+'.repeat(80) + '1', {})).toThrow(/too many tokens/)
    })
  })

  describe('resists sandbox escapes', () => {
    it.each([
      ['property access', 'a.b'],
      ['bracket access', 'a["b"]'],
      ['assignment', 'a = 1'],
      ['sequence', '1, 2'],
      ['template literal', '`x`'],
      ['arrow function', '() => 1'],
      ['prototype reach', '__proto__'],
    ])('rejects %s', (_name, formula) => {
      expect(() => evaluateSafeFormula(formula, { a: 1 })).toThrow()
    })
  })
})
