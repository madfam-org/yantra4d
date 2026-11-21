import { describe, it, expect } from 'vitest'
import { formatValue, nodesDrivenBy, paramRows, partsByNode, readGraph, socketRows } from './graphReadOnly'

const FLANGE = {
  version: '1.0.0',
  units: 'mm',
  nodes: [
    { id: 'outline', type: 'profile_circle', params: { r: 45 } },
    { id: 'plate', type: 'extrude', inputs: { profile: 'outline' }, params: { height: 8 } },
    { id: 'bore', type: 'cylinder', params: { r: 12, h: 400 } },
    { id: 'drilled', type: 'cut', inputs: { a: 'plate', b: 'bore' } },
  ],
  outputs: { flange: 'drilled', blank: 'drilled' },
}

// Graph 1.1: declared parameters, a derived chain, expressions.
const TWIN = {
  version: '1.1.0',
  parameters: { e_end: { default: 10 }, mirrored: { default: false } },
  derived: [
    { id: 'reach', expr: 'e_end * 2' },
    { id: 'reach_plus', expr: 'reach + 1' },
    { id: 'const_only', expr: '3 * 4' },
  ],
  nodes: [
    { id: 'post', type: 'box', params: { w: { expr: 'reach_plus' }, d: 5, h: 5 } },
    { id: 'arm', type: 'box', params: { w: { expr: 'const_only' }, d: 5, h: { expr: 'mirrored ? 2 : 3' } } },
    { id: 'path', type: 'profile_polyline', params: { points: [[0, 0], [{ expr: 'e_end' }, 1]] } },
  ],
  outputs: { body: 'post' },
}

const BINDINGS = { plate_radius: ['outline.r'], thickness: ['plate.height'] }

describe('readGraph', () => {
  it('parses a graph document', () => {
    expect(readGraph(JSON.stringify(FLANGE)).nodes).toHaveLength(4)
  })

  it('returns null for text that is not a graph instead of throwing', () => {
    expect(readGraph('not json')).toBeNull()
    expect(readGraph('[]')).toBeNull()
    expect(readGraph('{"nodes": "x"}')).toBeNull()
    expect(readGraph('{"nodes": [{"id": 1}]}')).toBeNull()
  })

  it('fills a missing outputs map', () => {
    expect(readGraph('{"nodes": []}').outputs).toEqual({})
  })
})

describe('paramRows', () => {
  it('reports a manifest binding with the bound parameter and its current value', () => {
    const rows = paramRows(FLANGE, FLANGE.nodes[0], BINDINGS, { plate_radius: 50 })
    expect(rows.find((r) => r.name === 'r').source).toEqual({ kind: 'bound', parameterId: 'plate_radius', value: 50 })
  })

  it('reports a written literal', () => {
    const rows = paramRows(FLANGE, FLANGE.nodes[2], BINDINGS)
    expect(rows.find((r) => r.name === 'h').source).toEqual({ kind: 'literal', value: 400 })
  })

  it('reports a catalog default for a param the node leaves out', () => {
    const rows = paramRows(FLANGE, FLANGE.nodes[0], BINDINGS)
    expect(rows.find((r) => r.name === 'plane').source).toEqual({ kind: 'default', value: 'XY' })
  })

  it('reports an expression and the manifest parameters it reads through derived values', () => {
    const rows = paramRows(TWIN, TWIN.nodes[0], {})
    expect(rows.find((r) => r.name === 'w').source).toEqual({ kind: 'expression', expr: 'reach_plus', reads: ['e_end'] })
  })

  it('reports an expression that reads no parameter', () => {
    const rows = paramRows(TWIN, TWIN.nodes[1], {})
    expect(rows.find((r) => r.name === 'w').source).toEqual({ kind: 'expression', expr: 'const_only', reads: [] })
  })

  it('reports expressions inside a list of points', () => {
    const row = paramRows(TWIN, TWIN.nodes[2], {}).find((r) => r.name === 'points')
    expect(row.source.kind).toBe('expression')
    expect(row.source.reads).toEqual(['e_end'])
    expect(row.source.expr).toBe('[[0,0],["e_end",1]]')
  })

  it('a node with no params has no rows', () => {
    expect(paramRows(FLANGE, FLANGE.nodes[3], BINDINGS)).toEqual([])
  })
})

describe('nodesDrivenBy', () => {
  it('follows manifest bindings', () => {
    expect([...nodesDrivenBy(FLANGE, BINDINGS, 'plate_radius')]).toEqual(['outline'])
  })

  it('follows a list binding to every target', () => {
    const map = { edge: ['outline.r', 'bore.r'] }
    expect([...nodesDrivenBy(FLANGE, map, 'edge')].sort()).toEqual(['bore', 'outline'])
  })

  it('follows expressions directly and through a derived chain', () => {
    expect([...nodesDrivenBy(TWIN, {}, 'e_end')].sort()).toEqual(['path', 'post'])
    expect([...nodesDrivenBy(TWIN, {}, 'mirrored')]).toEqual(['arm'])
  })

  it('is empty for a parameter the graph never reads', () => {
    expect(nodesDrivenBy(FLANGE, BINDINGS, 'unrelated').size).toBe(0)
    expect(nodesDrivenBy(TWIN, {}, 'unrelated').size).toBe(0)
  })
})

describe('socketRows', () => {
  it('lists each input socket and what is wired into it', () => {
    expect(socketRows(FLANGE.nodes[3])).toEqual([
      { socket: 'a', type: 'solid', from: 'plate' },
      { socket: 'b', type: 'solid', from: 'bore' },
    ])
  })

  it('reports an unconnected socket as null', () => {
    expect(socketRows({ id: 'x', type: 'extrude' })).toEqual([{ socket: 'profile', type: 'profile', from: null }])
  })
})

describe('formatValue and partsByNode', () => {
  it('formats values as one line', () => {
    expect(formatValue(45)).toBe('45')
    expect(formatValue('>Z')).toBe('>Z')
    expect(formatValue(true)).toBe('true')
    expect(formatValue({ expr: 'a + 1' })).toBe('a + 1')
    expect(formatValue([1, 2])).toBe('[1,2]')
    expect(formatValue(undefined)).toBe('')
  })

  it('groups output parts by node', () => {
    expect(partsByNode(FLANGE).get('drilled')).toEqual(['flange', 'blank'])
  })
})
