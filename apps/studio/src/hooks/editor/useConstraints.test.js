import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useConstraints } from './useConstraints'

const GRIDFINITY_CONSTRAINTS = [
  {
    rule: 'width_units * depth_units <= 24',
    message: { es: 'Máximo 24 celdas', en: 'Max 24 grid cells' },
    severity: 'warning',
    applies_to: ['width_units', 'depth_units'],
  },
  {
    rule: 'vertical_chambers * horizontal_chambers <= 12',
    message: { es: 'Máximo 12 compartimentos', en: 'Max 12 compartments' },
    severity: 'warning',
    applies_to: ['vertical_chambers', 'horizontal_chambers'],
  },
]

const ERROR_CONSTRAINT = [
  {
    rule: 'wall_thickness >= 1.2',
    message: { en: 'Minimum thickness for FDM printing' },
    severity: 'error',
    applies_to: ['wall_thickness'],
  },
]

describe('useConstraints', () => {
  it('returns empty when no constraints', () => {
    const { result } = renderHook(() => useConstraints(null, {}))
    expect(result.current.violations).toEqual([])
    expect(result.current.byParam).toEqual({})
    expect(result.current.hasErrors).toBe(false)
  })

  it('returns empty when constraints is empty array', () => {
    const { result } = renderHook(() => useConstraints([], {}))
    expect(result.current.violations).toEqual([])
    expect(result.current.hasErrors).toBe(false)
  })

  it('returns no violations when all constraints pass', () => {
    const params = { width_units: 2, depth_units: 1, vertical_chambers: 1, horizontal_chambers: 1 }
    const { result } = renderHook(() => useConstraints(GRIDFINITY_CONSTRAINTS, params))
    expect(result.current.violations).toEqual([])
    expect(result.current.hasErrors).toBe(false)
  })

  it('detects grid cell count violation', () => {
    const params = { width_units: 5, depth_units: 5, vertical_chambers: 1, horizontal_chambers: 1 }
    const { result } = renderHook(() => useConstraints(GRIDFINITY_CONSTRAINTS, params))
    expect(result.current.violations).toHaveLength(1)
    expect(result.current.violations[0].message.en).toBe('Max 24 grid cells')
    expect(result.current.violations[0].severity).toBe('warning')
  })

  // The 555 authored constraints across the commons use `expression`, not `rule`.
  // These lock in that the evaluator reads `expression` and derives applies_to.
  it('evaluates constraints authored with `expression` (the real manifest shape)', () => {
    const constraints = [
      { expression: 'grid_x * grid_y <= 24', severity: 'warning',
        message: { en: 'Large grids may be slow', es: 'Rejillas grandes pueden tardar' } },
    ]
    const passing = renderHook(() => useConstraints(constraints, { grid_x: 3, grid_y: 3 }))
    expect(passing.result.current.violations).toEqual([])
    const failing = renderHook(() => useConstraints(constraints, { grid_x: 6, grid_y: 6 }))
    expect(failing.result.current.violations).toHaveLength(1)
    expect(failing.result.current.violations[0].message.en).toBe('Large grids may be slow')
  })

  it('derives applies_to from the expression when not declared', () => {
    const constraints = [
      { expression: 'slot_w < plate_w', severity: 'error', message: { en: 'Slot too wide' } },
    ]
    const { result } = renderHook(() => useConstraints(constraints, { slot_w: 50, plate_w: 40 }))
    expect(result.current.hasErrors).toBe(true)
    // both referenced params should carry the violation so their controls light up
    expect(Object.keys(result.current.byParam).sort()).toEqual(['plate_w', 'slot_w'])
  })

  it('still supports legacy `rule` and prefers `expression` when both present', () => {
    const constraints = [
      { expression: 'a <= 1', rule: 'a <= 999', severity: 'warning', message: { en: 'x' } },
    ]
    const { result } = renderHook(() => useConstraints(constraints, { a: 5 }))
    // expression (a<=1) is violated at a=5; if it had used rule (a<=999) it would pass
    expect(result.current.violations).toHaveLength(1)
  })

  it('detects compartment count violation', () => {
    const params = { width_units: 2, depth_units: 1, vertical_chambers: 4, horizontal_chambers: 4 }
    const { result } = renderHook(() => useConstraints(GRIDFINITY_CONSTRAINTS, params))
    expect(result.current.violations).toHaveLength(1)
    expect(result.current.violations[0].appliesTo).toEqual(['vertical_chambers', 'horizontal_chambers'])
  })

  it('detects multiple violations simultaneously', () => {
    const params = { width_units: 6, depth_units: 6, vertical_chambers: 6, horizontal_chambers: 6 }
    const { result } = renderHook(() => useConstraints(GRIDFINITY_CONSTRAINTS, params))
    expect(result.current.violations).toHaveLength(2)
  })

  it('indexes violations by parameter ID', () => {
    const params = { width_units: 5, depth_units: 5, vertical_chambers: 1, horizontal_chambers: 1 }
    const { result } = renderHook(() => useConstraints(GRIDFINITY_CONSTRAINTS, params))
    expect(result.current.byParam['width_units']).toHaveLength(1)
    expect(result.current.byParam['depth_units']).toHaveLength(1)
    expect(result.current.byParam['vertical_chambers']).toBeUndefined()
  })

  it('hasErrors is true only for error severity', () => {
    const params = { wall_thickness: 0.8 }
    const { result } = renderHook(() => useConstraints(ERROR_CONSTRAINT, params))
    expect(result.current.hasErrors).toBe(true)
    expect(result.current.violations).toHaveLength(1)
  })

  it('hasErrors is false for warning-only violations', () => {
    const params = { width_units: 5, depth_units: 5, vertical_chambers: 1, horizontal_chambers: 1 }
    const { result } = renderHook(() => useConstraints(GRIDFINITY_CONSTRAINTS, params))
    expect(result.current.violations).toHaveLength(1)
    expect(result.current.hasErrors).toBe(false)
  })

  it('skips constraints with missing params gracefully', () => {
    const params = { width_units: 2 } // depth_units missing
    const { result } = renderHook(() => useConstraints(GRIDFINITY_CONSTRAINTS, params))
    // Should not throw — skips constraints that fail to evaluate
    expect(result.current).toBeDefined()
  })

  it('supports boolean logic without dynamic code evaluation', () => {
    const constraints = [
      {
        rule: '(width_units >= 1 && depth_units >= 1) || force_override == 1',
        message: { en: 'Dimensions must be positive' },
        severity: 'error',
        applies_to: ['width_units', 'depth_units'],
      },
    ]
    const { result } = renderHook(() => useConstraints(constraints, {
      width_units: 0,
      depth_units: 1,
      force_override: 0,
    }))
    expect(result.current.violations).toHaveLength(1)
    expect(result.current.hasErrors).toBe(true)
  })
})
