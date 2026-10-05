import { describe, it, expect } from 'vitest'
import * as B from './graphBindings'

const parameters = [
  { id: 'plate_radius', type: 'slider', binding: 'outline.r' },
  { id: 'edge_chamfer', type: 'slider', binding: ['flange.distance', 'blank.distance'] },
  { id: 'thickness', type: 'slider' },
  { id: 'bearing', type: 'select', options: [{ value: '608' }, { value: 625 }] },
  { id: 'nema', type: 'select', options: [{ value: 'NEMA17' }] },
  { id: 'empty_select', type: 'select', options: [] },
  { id: 'label', type: 'text' },
  { id: 'mirrored', type: 'checkbox' },
]

describe('bindingsFromManifest', () => {
  it('normalises every binding to a list', () => {
    expect(B.bindingsFromManifest(parameters)).toEqual({
      plate_radius: ['outline.r'],
      edge_chamfer: ['flange.distance', 'blank.distance'],
    })
  })

  it('tolerates a missing parameter list and junk entries', () => {
    expect(B.bindingsFromManifest(undefined)).toEqual({})
    expect(B.bindingsFromManifest([null, { id: 'x', binding: [3] }])).toEqual({})
  })
})

describe('boundParameter / setBinding', () => {
  const map = B.bindingsFromManifest(parameters)

  it('finds the parameter driving a node param', () => {
    expect(B.boundParameter(map, 'blank', 'distance')).toBe('edge_chamfer')
    expect(B.boundParameter(map, 'outline', 'x')).toBeNull()
  })

  it('moves a target from one driver to another — one driver per node param', () => {
    const next = B.setBinding(map, 'outline', 'r', 'thickness')
    expect(next.plate_radius).toBeUndefined()
    expect(next.thickness).toEqual(['outline.r'])
  })

  it('appends to a parameter that already drives something', () => {
    expect(B.setBinding(map, 'cap', 'distance', 'edge_chamfer').edge_chamfer).toEqual([
      'flange.distance', 'blank.distance', 'cap.distance',
    ])
  })

  it('unbinds with null', () => {
    const next = B.setBinding(map, 'flange', 'distance', null)
    expect(next.edge_chamfer).toEqual(['blank.distance'])
  })
})

describe('dropNodeBindings', () => {
  it('drops every target on a removed node, and only on it', () => {
    const map = { a: ['plate.height', 'plate2.height'], b: ['plate.r'] }
    expect(B.dropNodeBindings(map, 'plate')).toEqual({ a: ['plate2.height'] })
  })
})

describe('bindingChanges', () => {
  it('is empty when nothing changed', () => {
    const map = B.bindingsFromManifest(parameters)
    expect(B.bindingChanges(map, structuredClone(map))).toEqual({})
  })

  it('sends a single target as a string, several as a list, and removals as null', () => {
    const before = { a: ['x.r'], b: ['y.h', 'z.h'], c: ['w.r'] }
    const after = { a: ['x.r', 'q.r'], b: ['y.h'], d: ['v.r'] }
    expect(B.bindingChanges(before, after)).toEqual({ a: ['x.r', 'q.r'], b: 'y.h', c: null, d: 'v.r' })
  })
})

describe('bindableParameters', () => {
  it('keeps sliders and all-numeric selects only', () => {
    expect(B.bindableParameters(parameters).map((p) => p.id)).toEqual([
      'plate_radius', 'edge_chamfer', 'thickness', 'bearing',
    ])
    expect(B.bindableParameters(undefined)).toEqual([])
  })
})

describe('bindingKey', () => {
  it('joins node and param the way the manifest writes them', () => {
    expect(B.bindingKey('outline', 'r')).toBe('outline.r')
  })
})
