import { describe, it, expect } from 'vitest'
import * as E from './graphExpressions'

const base = () => ({
  version: '1.0.0',
  units: 'mm',
  nodes: [{ id: 'body', type: 'box', params: { w: 10 } }],
  outputs: { part: 'body' },
})

describe('expressionIdentifiers', () => {
  it('lists each identifier once, in first-use order, skipping numbers', () => {
    expect(E.expressionIdentifiers('width / 2 - wall + width * 0.5')).toEqual(['width', 'wall'])
  })

  it('scans like the safeFormula tokenizer: a number ends before an identifier starts', () => {
    expect(E.expressionIdentifiers('2abc + .5 + x1')).toEqual(['abc', 'x1'])
  })

  it('returns nothing for a literal', () => {
    expect(E.expressionIdentifiers('3.25 * 4')).toEqual([])
  })
})

describe('declaredValue', () => {
  it('uses numbers and booleans as they are', () => {
    expect(E.declaredValue({ default: 30 })).toBe(30)
    expect(E.declaredValue({ default: false })).toBe(false)
  })

  it('parses a numeric string', () => {
    expect(E.declaredValue({ default: '608' })).toBe(608)
  })

  it('reads a named option through the map', () => {
    expect(E.declaredValue({ default: 'NEMA17', map: { NEMA17: 17, NEMA23: 23 } })).toBe(17)
  })

  it('has no value for a named option without a map', () => {
    expect(E.declaredValue({ default: 'NEMA17' })).toBeUndefined()
    expect(E.declaredValue({ default: '' })).toBeUndefined()
    expect(E.declaredValue({ default: Number.NaN })).toBeUndefined()
  })

  it('prefers the manifest default, which is what a render reads', () => {
    expect(E.declaredValue({ default: 30 }, 42)).toBe(42)
    expect(E.declaredValue({ default: 'NEMA17', map: { NEMA17: 17, NEMA23: 23 } }, 'NEMA23')).toBe(23)
  })
})

describe('needsMap', () => {
  it('is true only for a select with a non-numeric option', () => {
    expect(E.needsMap({ id: 'nema', type: 'select', options: [{ value: 'NEMA17' }, { value: 'NEMA23' }] })).toBe(true)
    expect(E.needsMap({ id: 'bearing', type: 'select', options: [{ value: '608' }, { value: 625 }] })).toBe(false)
    expect(E.needsMap({ id: 'od', type: 'slider' })).toBe(false)
  })
})

describe('buildScope', () => {
  it('evaluates declared parameters and derived values in order', () => {
    const doc = {
      ...base(),
      parameters: { b_od: { default: 22 }, press_fit: { default: 0.1 } },
      derived: [
        { id: 'seat_r', expr: 'b_od / 2 + press_fit / 2' },
        { id: 'wall', expr: 'seat_r + 2' },
      ],
    }
    const { scope, issues } = E.buildScope(doc)
    expect(issues).toEqual([])
    expect(scope.seat_r).toBeCloseTo(11.05)
    expect(scope.wall).toBeCloseTo(13.05)
  })

  it('refuses a derived value that reads a later one', () => {
    const doc = { ...base(), parameters: { a: { default: 1 } }, derived: [{ id: 'x', expr: 'y + a' }, { id: 'y', expr: 'a' }] }
    const { issues } = E.buildScope(doc)
    expect(issues).toHaveLength(1)
    expect(issues[0]).toMatchObject({ derivedId: 'x' })
    expect(issues[0].message).toMatch(/"y"/)
  })

  it('refuses duplicates, collisions with parameters and bad ids', () => {
    const doc = {
      ...base(),
      parameters: { a: { default: 1 }, 'bad-id': { default: 1 }, nodefault: {} },
      derived: [{ id: 'x', expr: 'a' }, { id: 'x', expr: 'a' }, { id: 'a', expr: '1' }, { id: '9z', expr: '1' }],
    }
    const messages = E.buildScope(doc).issues.map((i) => i.message)
    expect(messages).toEqual(expect.arrayContaining([
      expect.stringMatching(/"bad-id" is not a plain identifier/),
      expect.stringMatching(/"nodefault" needs a default/),
      expect.stringMatching(/"x" is defined twice/),
      expect.stringMatching(/"a" is defined twice/),
      expect.stringMatching(/"9z"/),
    ]))
  })

  it('refuses a named-option default without a map, as the engine does', () => {
    const doc = { ...base(), parameters: { nema: { default: 'NEMA17' } }, derived: [{ id: 'size', expr: 'nema * 2' }] }
    const { issues } = E.buildScope(doc)
    expect(issues[0].message).toMatch(/"NEMA17", which is neither numeric nor in its map/)
    // and the derived value that reads it cannot be evaluated either
    expect(issues[1].message).toMatch(/Missing numeric parameter: nema/)
  })

  it('accepts the same declaration once the map names the default', () => {
    const doc = { ...base(), parameters: { nema: { default: 'NEMA17', map: { NEMA17: 17 } } }, derived: [{ id: 'size', expr: 'nema * 2' }] }
    const { scope, issues } = E.buildScope(doc)
    expect(issues).toEqual([])
    expect(scope.size).toBe(34)
  })

  it('refuses reserved names, unknown keys and malformed maps', () => {
    const doc = {
      ...base(),
      parameters: {
        result: { default: 1 },
        extra: { default: 1, unit: 'mm' },
        badmap: { default: 'a', map: { 'a/b': 1 } },
        nanmap: { default: 'a', map: { a: 'x' } },
        emptymap: { default: 1, map: {} },
        weird: { default: { nested: true } },
        inf: { default: Infinity },
      },
      derived: [{ id: 'cq', expr: '1' }, { id: 'ok', expr: '1', note: 'x' }],
    }
    const messages = E.buildScope(doc).issues.map((i) => i.message).join('\n')
    expect(messages).toMatch(/"result" is a reserved name/)
    expect(messages).toMatch(/"extra" has unknown keys: unit/)
    expect(messages).toMatch(/"badmap" maps "a\/b"/)
    expect(messages).toMatch(/"nanmap" maps "a" to something that is not a number/)
    expect(messages).toMatch(/"emptymap" has an empty or malformed 'map'/)
    expect(messages).toMatch(/"weird" has a default that is not a number/)
    expect(messages).toMatch(/"inf" has a default that is not finite/)
    expect(messages).toMatch(/"cq" is a reserved name/)
    expect(messages).toMatch(/"ok" must have exactly "id" and "expr"/)
  })

  it('takes manifest defaults over declared fallbacks', () => {
    const doc = { ...base(), parameters: { od: { default: 30 } } }
    expect(E.buildScope(doc, { od: 50 }).scope.od).toBe(50)
  })
})

describe('checkExpression', () => {
  const declared = { width: { default: 40 }, wall: { default: 2 } }
  const scope = { width: 40, wall: 2, inner: 36 }

  it('evaluates a valid expression', () => {
    expect(E.checkExpression('width / 2 - wall', declared, scope, [])).toEqual({ value: 18, undeclared: [] })
  })

  it('may read derived ids it is allowed to see', () => {
    expect(E.checkExpression('inner / 2', declared, scope, ['inner']).value).toBe(18)
  })

  it('names identifiers that are not declared', () => {
    const check = E.checkExpression('width + height', declared, scope, [])
    expect(check.undeclared).toEqual(['height'])
    expect(check.error).toMatch(/"height"/)
  })

  it('reports an empty expression and a syntax error', () => {
    expect(E.checkExpression('  ', declared, scope, []).error).toMatch(/empty/)
    expect(E.checkExpression(42, declared, scope, []).error).toMatch(/empty/)
    expect(E.checkExpression('width +', declared, scope, []).error).toBeTruthy()
  })
})

describe('version', () => {
  it('needs 1.1 only when declarations are used', () => {
    expect(E.requiredVersion(base())).toBe('1.0')
    expect(E.requiredVersion({ ...base(), parameters: {} })).toBe('1.0')
    expect(E.requiredVersion({ ...base(), parameters: { a: { default: 1 } } })).toBe('1.1')
    expect(E.requiredVersion({ ...base(), derived: [{ id: 'x', expr: '1' }] })).toBe('1.1')
  })

  it('compares minor versions', () => {
    expect(E.versionAtLeast11('1.1.0')).toBe(true)
    expect(E.versionAtLeast11('1.2')).toBe(true)
    expect(E.versionAtLeast11('1.0.0')).toBe(false)
    expect(E.versionAtLeast11(undefined)).toBe(false)
  })
})

describe('declaration edits', () => {
  it('declaring a parameter bumps the document to 1.1', () => {
    const next = E.declareParameter(base(), 'od', { default: 30 })
    expect(next.parameters).toEqual({ od: { default: 30 } })
    expect(next.version).toBe('1.1.0')
  })

  it('keeps a version that is already 1.1 or later', () => {
    const next = E.declareParameter({ ...base(), version: '1.2.0' }, 'od', { default: 30 })
    expect(next.version).toBe('1.2.0')
  })

  it('refuses an id that is not an identifier, or is reserved', () => {
    expect(() => E.declareParameter(base(), 'bad-id', { default: 1 })).toThrow(/identifier/)
    expect(() => E.declareParameter(base(), 'math', { default: 1 })).toThrow(/reserved/)
    expect(() => E.addDerived(base(), 'lambda', '1')).toThrow(/reserved/)
  })

  it('undeclaring the last parameter removes the key', () => {
    const doc = E.declareParameter(base(), 'od', { default: 30 })
    expect(E.undeclareParameter(doc, 'od').parameters).toBeUndefined()
  })

  it('sets and clears a map, and refuses an undeclared id', () => {
    let doc = E.declareParameter(base(), 'nema', { default: 'NEMA17' })
    doc = E.setParameterMap(doc, 'nema', { NEMA17: 17 })
    expect(doc.parameters.nema).toEqual({ default: 'NEMA17', map: { NEMA17: 17 } })
    doc = E.setParameterMap(doc, 'nema', null)
    expect(doc.parameters.nema).toEqual({ default: 'NEMA17' })
    expect(() => E.setParameterMap(doc, 'ghost', {})).toThrow(/not declared/)
  })

  it('adds, edits, reorders and removes derived values', () => {
    let doc = E.declareParameter(base(), 'a', { default: 1 })
    doc = E.addDerived(doc, 'x', 'a + 1')
    doc = E.addDerived(doc, 'y', 'x * 2')
    expect(() => E.addDerived(doc, 'x', '1')).toThrow(/already defined/)
    expect(() => E.addDerived(doc, 'a', '1')).toThrow(/already defined/)
    expect(() => E.addDerived(doc, 'no good', '1')).toThrow(/identifier/)
    doc = E.setDerivedExpr(doc, 'y', 'x * 3')
    expect(doc.derived[1]).toEqual({ id: 'y', expr: 'x * 3' })
    doc = E.moveDerived(doc, 'y', -1)
    expect(doc.derived.map((d) => d.id)).toEqual(['y', 'x'])
    expect(E.moveDerived(doc, 'y', -1)).toBe(doc)
    expect(E.moveDerived(doc, 'ghost', 1)).toBe(doc)
    doc = E.removeDerived(E.removeDerived(doc, 'x'), 'y')
    expect(doc.derived).toBeUndefined()
  })

  it('never mutates its input', () => {
    const doc = base()
    const before = JSON.stringify(doc)
    E.addDerived(E.declareParameter(doc, 'a', { default: 1 }), 'x', 'a')
    expect(JSON.stringify(doc)).toBe(before)
  })
})
