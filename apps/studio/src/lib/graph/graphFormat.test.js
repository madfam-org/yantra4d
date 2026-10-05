import { describe, it, expect } from 'vitest'
import { formatLike } from './graphFormat'
import {
  addNode,
  parseGraph,
  removeNode,
  serializeGraph,
  setNodeParam,
  setNodePosition,
} from './graphDocument'

// The commons' graph documents at solid-hyperobjects 7de3a32e, byte for byte
// (see src/test/fixtures/commons-graphs/NOTICE).
const COMMONS = import.meta.glob('../../test/fixtures/commons-graphs/*/*.graph.json', {
  query: '?raw',
  import: 'default',
  eager: true,
})
const commons = Object.entries(COMMONS).map(([path, text]) => [path.split('commons-graphs/')[1], text])

// The ten printed parts of assembly A, plus the toolhead proxy: every commons
// cartridge whose mode declares a graph twin of its main.py.
const TWINS = [
  'ab-drive/ab-drive.graph.json',
  'ab-front-idler/front-idler.graph.json',
  'bed-extrusion-mount/bed-mount.graph.json',
  'corner-idler-bracket/corner-idler.graph.json',
  'idler-608/idler.graph.json',
  'toolhead-proxy/toolhead.graph.json',
  'x-carriage/x-carriage.graph.json',
  'xy-joint/xy-joint.graph.json',
  'z-belt-clamp/z-belt-clamp.graph.json',
  'z-drive-housing/z-drive.graph.json',
  'z-joint/z-joint.graph.json',
]

const source = (name) => commons.find(([n]) => n === name)[1]

/** Lines of `b` that are not lines of `a`, and the reverse. */
function lineDiff(a, b) {
  const la = a.split('\n')
  const lb = b.split('\n')
  const count = (lines) => lines.reduce((m, l) => m.set(l, (m.get(l) ?? 0) + 1), new Map())
  const ca = count(la)
  const cb = count(lb)
  const only = (x, y) => [...x].flatMap(([l, n]) => Array(Math.max(0, n - (y.get(l) ?? 0))).fill(l))
  return { added: only(cb, ca), removed: only(ca, cb) }
}

describe('graph documents keep their layout through a save', () => {
  it('has every commons graph document, the twins among them', () => {
    expect(commons.length).toBe(15)
    for (const twin of TWINS) expect(commons.map(([n]) => n)).toContain(twin)
  })

  it.each(commons)('%s: load and save with no edit is byte-identical', (_name, text) => {
    // The editor's own path: validate and parse, then write with the source in hand.
    const doc = parseGraph(text)
    expect(serializeGraph(doc, text)).toBe(text)
    // A structurally identical copy (no shared references) too.
    expect(formatLike(JSON.parse(text), text)).toBe(text)
  })

  it.each(TWINS)('%s: a one-parameter edit changes one line', (name) => {
    const text = source(name)
    const doc = parseGraph(text)
    const node = doc.nodes.find((n) => n.params && Object.keys(n.params).length > 0)
    const param = Object.keys(node.params)[0]
    const out = serializeGraph(setNodeParam(doc, node.id, param, { expr: '1 + 2' }), text)
    const { added, removed } = lineDiff(text, out)
    expect(removed).toHaveLength(1)
    expect(added).toHaveLength(1)
    expect(added[0]).toContain('"expr": "1 + 2"')
    expect(added[0]).toContain(`"id": "${node.id}"`)
    expect(out.split('\n')).toHaveLength(text.split('\n').length)
    expect(JSON.parse(out)).toEqual(JSON.parse(JSON.stringify(setNodeParam(doc, node.id, param, { expr: '1 + 2' }))))
  })

  it('keeps 14.0 as 14.0 and keeps the decimal spelling of a changed whole number', () => {
    const text = source('bed-extrusion-mount/bed-mount.graph.json')
    expect(text).toContain('"screw_offset": {"default": 14.0}')
    const doc = parseGraph(text)
    const unchanged = serializeGraph({ ...doc, parameters: { ...doc.parameters, plate_t: { default: 5 } } }, text)
    expect(unchanged).toContain('"screw_offset": {"default": 14.0}')
    expect(lineDiff(text, unchanged).added).toEqual(['    "plate_t": {"default": 5}'])
    const edited = serializeGraph({ ...doc, parameters: { ...doc.parameters, screw_offset: { default: 15 } } }, text)
    expect(lineDiff(text, edited).added).toEqual(['    "screw_offset": {"default": 15.0},'])
  })

  it('moving a node rewrites only that node, on one line', () => {
    const text = source('bed-extrusion-mount/bed-mount.graph.json')
    const out = serializeGraph(setNodePosition(parseGraph(text), 'stem', { x: 120.4, y: 40 }), text)
    const { added, removed } = lineDiff(text, out)
    expect(removed).toHaveLength(1)
    expect(added).toHaveLength(1)
    expect(added[0]).toMatch(/^ {4}\{"id": "stem", .*"meta": \{"position": \{"x": 120, "y": 40\}\}\},$/)
  })

  it('adding and removing a node touches only that node\'s line', () => {
    const text = source('flange-plate/flange.graph.json')
    const doc = parseGraph(text)
    const added = addNode(doc, 'box')
    const created = added.nodes[added.nodes.length - 1]
    const out = serializeGraph(added, text)
    const diff = lineDiff(text, out)
    // The new node, plus the previous last node gaining its trailing comma.
    expect(diff.added).toHaveLength(2)
    expect(diff.removed).toHaveLength(1)
    expect(diff.added.some((l) => l.includes(`"id": "${created.id}"`) && !l.includes('\n'))).toBe(true)
    // And removing it again restores the original text exactly.
    expect(serializeGraph(removeNode(parseGraph(out), created.id), out)).toBe(text)
  })

  it('removing a node in the middle drops exactly its line', () => {
    const text = source('bed-extrusion-mount/bed-mount.graph.json')
    const doc = parseGraph(text)
    const victim = 'cross_tongue'
    const next = { ...doc, nodes: doc.nodes.filter((n) => n.id !== victim) }
    const { added, removed } = lineDiff(text, serializeGraph(next, text))
    expect(added).toEqual([])
    expect(removed).toHaveLength(1)
    expect(removed[0]).toContain(`"id": "${victim}"`)
  })

  it('a two-space document stays two-space, and an edit touches one line', () => {
    const doc = { version: '1.1.0', units: 'mm', nodes: [{ id: 'a', type: 'box', params: { w: 14.0, d: 2 } }], outputs: { body: 'a' } }
    const pretty = `${JSON.stringify(doc, null, 2)}\n`
    expect(formatLike(doc, pretty)).toBe(pretty)
    const out = formatLike({ ...doc, nodes: [{ ...doc.nodes[0], params: { w: 14, d: 3 } }] }, pretty)
    expect(lineDiff(pretty, out)).toEqual({ added: ['        "d": 3'], removed: ['        "d": 2'] })
  })

  it('writes new containers in the style of their neighbours', () => {
    const multi = '{\n  "a": {\n    "x": 1\n  }\n}\n'
    expect(formatLike({ a: { x: 1 }, b: { y: [1, 2] } }, multi))
      .toBe('{\n  "a": {\n    "x": 1\n  },\n  "b": {\n    "y": [\n      1,\n      2\n    ]\n  }\n}\n')
    const oneLine = '{\n  "nodes": [\n    {"id": "a", "type": "box"}\n  ]\n}\n'
    expect(formatLike({ nodes: [{ id: 'a', type: 'box' }, { id: 'b', type: 'sphere', params: { r: 2 } }] }, oneLine))
      .toBe('{\n  "nodes": [\n    {"id": "a", "type": "box"},\n    {"id": "b", "type": "sphere", "params": {"r": 2}}\n  ]\n}\n')
  })

  it('keeps empty containers and whitespace it does not touch', () => {
    expect(formatLike({ a: [], b: 2 }, '{ "a": [ ], "b": 1 }')).toBe('{ "a": [ ], "b": 2 }')
    expect(formatLike({ a: [1] }, '{"a": []}')).toBe('{"a": [1]}')
    expect(formatLike({ a: [] }, '{"a": [1, 2]}')).toBe('{"a": []}')
  })

  it('writes a reordered object afresh rather than mislabelling its members', () => {
    const out = formatLike({ b: 2, a: 1 }, '{"a": 1, "b": 2}')
    expect(JSON.parse(out)).toEqual({ b: 2, a: 1 })
    expect(Object.keys(JSON.parse(out))).toEqual(['b', 'a'])
  })

  it('falls back to two-space JSON without a usable source', () => {
    const doc = { version: '1.0.0', nodes: [] }
    const plain = `${JSON.stringify(doc, null, 2)}\n`
    expect(formatLike(doc, undefined)).toBe(plain)
    expect(formatLike(doc, '')).toBe(plain)
    expect(formatLike(doc, '{"version": "1.0.0", "nodes": [')).toBe(plain)
    expect(formatLike(doc, '{"a": 1} trailing')).toBe(plain)
    expect(serializeGraph(doc)).toBe(plain)
  })

  it('reads escaped strings, exponents, literals and surrounding whitespace', () => {
    const text = '\n  {"s": "a\\"b\\\\", "n": -1.5e3, "t": true, "f": false, "z": null}  \n'
    expect(formatLike(JSON.parse(text), text)).toBe(text)
    expect(formatLike({ ...JSON.parse(text), t: false }, text))
      .toBe('\n  {"s": "a\\"b\\\\", "n": -1.5e3, "t": false, "f": false, "z": null}  \n')
  })

  it('matches array items by position when they carry no id', () => {
    const text = '{"points": [[0, 0], [10.0, 0], [10, 5]]}'
    expect(formatLike({ points: [[0, 0], [10, 0], [10, 6]] }, text)).toBe('{"points": [[0, 0], [10.0, 0], [10, 6]]}')
    expect(formatLike({ points: [[0, 0], [10, 0], [10, 5], [0, 5]] }, text))
      .toBe('{"points": [[0, 0], [10.0, 0], [10, 5], [0, 5]]}')
  })
})
