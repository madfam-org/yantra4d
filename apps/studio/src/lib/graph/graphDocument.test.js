import { describe, it, expect } from 'vitest'
import * as G from './graphDocument'

/** A small valid graph: a plate with a bore, chamfered. */
function makeDoc() {
  return {
    version: '1.0.0',
    units: 'mm',
    nodes: [
      { id: 'base', type: 'box', params: { w: 60, d: 40, h: 8 } },
      { id: 'bore', type: 'cylinder', params: { r: 3, h: 40 } },
      { id: 'body', type: 'cut', inputs: { a: 'base', b: 'bore' } },
      { id: 'soft', type: 'chamfer', inputs: { shape: 'body' }, params: { edges: '|Z', distance: 1 } },
    ],
    outputs: { part: 'soft' },
  }
}

describe('node catalog', () => {
  it('carries the whole server vocabulary', () => {
    const names = G.nodeTypeNames()
    expect(names).toContain('box')
    expect(names).toContain('extrude')
    expect(names).toContain('pattern_polar')
    expect(names.length).toBeGreaterThanOrEqual(19)
  })

  it('splits producers by output type', () => {
    expect(G.nodeTypesByOutput('profile')).toEqual([
      'profile_circle',
      'profile_polygon',
      'profile_rect',
    ])
    expect(G.nodeTypesByOutput('solid')).toContain('box')
    expect(G.nodeTypesByOutput('solid')).not.toContain('profile_rect')
  })

  it('exposes the server limits rather than hardcoding them', () => {
    expect(G.LIMITS.max_pattern_count).toBe(200)
    expect(G.LIMITS.max_nodes).toBe(500)
  })

  it('marks structural params as not bindable', () => {
    expect(G.NODE_TYPES.profile_rect.params.plane.bindable).toBe(false)
    expect(G.NODE_TYPES.profile_rect.params.w.bindable).toBe(true)
    expect(G.NODE_TYPES.pattern_linear.params.count.bindable).toBe(true)
  })

  it('supplies defaults straight from the server', () => {
    expect(G.defaultParams('box')).toEqual({ w: 10, d: 10, h: 10 })
    expect(G.defaultParams('nope')).toEqual({})
  })
})

describe('validateGraph', () => {
  it('accepts a good document', () => {
    expect(G.validateGraph(makeDoc())).toEqual([])
  })

  it.each([null, 'text', 42, []])('rejects non-object document %s', (bad) => {
    expect(G.validateGraph(bad)[0].message).toMatch(/JSON object/)
  })

  it.each(['2.0.0', '0.9', 'one', undefined])('rejects version %s', (version) => {
    const issues = G.validateGraph({ ...makeDoc(), version })
    expect(issues.some((i) => /Version/.test(i.message))).toBe(true)
  })

  it('rejects non-millimetre units', () => {
    const issues = G.validateGraph({ ...makeDoc(), units: 'in' })
    expect(issues.some((i) => /millimetre/.test(i.message))).toBe(true)
  })

  it('requires at least one node', () => {
    expect(G.validateGraph({ ...makeDoc(), nodes: [] })[0].message).toMatch(/at least one node/)
    expect(G.validateGraph({ ...makeDoc(), nodes: 'x' })[0].message).toBeTruthy()
  })

  it('flags too many nodes', () => {
    const nodes = Array.from({ length: 501 }, (_, i) => ({ id: `n${i}`, type: 'box' }))
    const issues = G.validateGraph({ ...makeDoc(), nodes, outputs: { part: 'n0' } })
    expect(issues.some((i) => /Too many nodes/.test(i.message))).toBe(true)
  })

  it.each(['1bad', 'a-b', '', null])('rejects node id %s', (id) => {
    const doc = makeDoc()
    doc.nodes.push({ id, type: 'box' })
    expect(G.validateGraph(doc).some((i) => /must start with a letter/.test(i.message))).toBe(true)
  })

  it('rejects duplicate ids', () => {
    const doc = makeDoc()
    doc.nodes.push({ id: 'base', type: 'sphere' })
    expect(G.validateGraph(doc).some((i) => /Duplicate node id/.test(i.message))).toBe(true)
  })

  it('rejects unknown node types and unknown params', () => {
    const doc = makeDoc()
    doc.nodes.push({ id: 'weird', type: 'loft' })
    doc.nodes[0].params.radius = 5
    const issues = G.validateGraph(doc)
    expect(issues.some((i) => /Unknown node type/.test(i.message))).toBe(true)
    expect(issues.some((i) => /has no parameter "radius"/.test(i.message))).toBe(true)
  })

  it('reports missing and unexpected inputs', () => {
    const doc = makeDoc()
    doc.nodes[2].inputs = { a: 'base', c: 'bore' }
    const issues = G.validateGraph(doc)
    expect(issues.some((i) => /Missing input "b"/.test(i.message))).toBe(true)
    expect(issues.some((i) => /has no input "c"/.test(i.message))).toBe(true)
  })

  it('rejects a self-referencing input', () => {
    const doc = makeDoc()
    doc.nodes[3].inputs.shape = 'soft'
    expect(G.validateGraph(doc).some((i) => /connects the node to itself/.test(i.message))).toBe(true)
  })

  it('rejects a dangling reference', () => {
    const doc = makeDoc()
    doc.nodes[3].inputs.shape = 'ghost'
    expect(G.validateGraph(doc).some((i) => /unknown node "ghost"/.test(i.message))).toBe(true)
  })

  it('rejects a profile where a solid belongs, and vice versa', () => {
    const solidIntoExtrude = {
      version: '1.0.0',
      nodes: [
        { id: 'b', type: 'box' },
        { id: 'e', type: 'extrude', inputs: { profile: 'b' } },
      ],
      outputs: { part: 'e' },
    }
    expect(
      G.validateGraph(solidIntoExtrude).some((i) => /needs a profile.*produces a solid/.test(i.message)),
    ).toBe(true)

    const profileIntoCut = {
      version: '1.0.0',
      nodes: [
        { id: 'p', type: 'profile_rect' },
        { id: 'b', type: 'box' },
        { id: 'c', type: 'cut', inputs: { a: 'b', b: 'p' } },
      ],
      outputs: { part: 'c' },
    }
    expect(
      G.validateGraph(profileIntoCut).some((i) => /needs a solid.*produces a profile/.test(i.message)),
    ).toBe(true)
  })

  it('reports a cycle with the nodes involved', () => {
    const doc = {
      version: '1.0.0',
      nodes: [
        { id: 'a', type: 'translate', inputs: { shape: 'b' } },
        { id: 'b', type: 'translate', inputs: { shape: 'a' } },
      ],
      outputs: { part: 'a' },
    }
    const issue = G.validateGraph(doc).find((i) => /loop/.test(i.message))
    expect(issue.message).toMatch(/a/)
    expect(issue.message).toMatch(/b/)
  })

  it('requires outputs, and requires them to be solids', () => {
    expect(G.validateGraph({ ...makeDoc(), outputs: {} }).some((i) => /at least one output/.test(i.message))).toBe(true)
    expect(G.validateGraph({ ...makeDoc(), outputs: null }).some((i) => /at least one output/.test(i.message))).toBe(true)

    const doc = makeDoc()
    doc.nodes.push({ id: 'sketch', type: 'profile_rect' })
    doc.outputs.flat = 'sketch'
    expect(G.validateGraph(doc).some((i) => /extrude it into a solid/.test(i.message))).toBe(true)

    doc.outputs.flat = 'missing'
    expect(G.validateGraph(doc).some((i) => /unknown node "missing"/.test(i.message))).toBe(true)
  })

  it('flags too many outputs', () => {
    const doc = makeDoc()
    for (let i = 0; i < 51; i += 1) doc.outputs[`p${i}`] = 'soft'
    expect(G.validateGraph(doc).some((i) => /Too many outputs/.test(i.message))).toBe(true)
  })
})

describe('graph traversal', () => {
  it('orders nodes after their dependencies', () => {
    const order = G.topologicalOrder(makeDoc().nodes)
    expect(order.indexOf('base')).toBeLessThan(order.indexOf('body'))
    expect(order.indexOf('bore')).toBeLessThan(order.indexOf('body'))
    expect(order.indexOf('body')).toBeLessThan(order.indexOf('soft'))
  })

  it('returns null for a cyclic graph', () => {
    const nodes = [
      { id: 'a', type: 'translate', inputs: { shape: 'b' } },
      { id: 'b', type: 'translate', inputs: { shape: 'a' } },
    ]
    expect(G.topologicalOrder(nodes)).toBeNull()
  })

  it('finds every distinct cycle once', () => {
    const nodes = [
      { id: 'a', type: 'translate', inputs: { shape: 'b' } },
      { id: 'b', type: 'translate', inputs: { shape: 'a' } },
      { id: 'c', type: 'translate', inputs: { shape: 'd' } },
      { id: 'd', type: 'translate', inputs: { shape: 'c' } },
      { id: 'lone', type: 'box' },
    ]
    expect(G.findCycles(nodes)).toHaveLength(2)
  })

  it('survives a deep chain without blowing the stack', () => {
    const nodes = [{ id: 'n0', type: 'box' }]
    for (let i = 1; i < 400; i += 1) {
      nodes.push({ id: `n${i}`, type: 'translate', inputs: { shape: `n${i - 1}` } })
    }
    expect(G.findCycles(nodes)).toEqual([])
    expect(G.topologicalOrder(nodes)).toHaveLength(400)
  })

  it('collects downstream nodes', () => {
    const down = G.downstreamOf(makeDoc().nodes, 'base')
    expect([...down].sort()).toEqual(['base', 'body', 'soft'])
    expect(G.downstreamOf(makeDoc().nodes, 'soft')).toEqual(new Set(['soft']))
  })

  it('predicts cycles before connecting', () => {
    const { nodes } = makeDoc()
    expect(G.wouldCycle(nodes, 'soft', 'base')).toBe(true)
    expect(G.wouldCycle(nodes, 'base', 'base')).toBe(true)
    expect(G.wouldCycle(nodes, 'bore', 'soft')).toBe(false)
  })

  it('generates unused node ids', () => {
    const nodes = [{ id: 'box_1', type: 'box' }]
    expect(G.uniqueNodeId(nodes, 'box')).toBe('box_2')
    expect(G.uniqueNodeId([], 'profile_rect')).toBe('profile_rect_1')
  })
})

describe('edits', () => {
  it('adds a node with server defaults and leaves the original untouched', () => {
    const doc = makeDoc()
    const next = G.addNode(doc, 'sphere')
    expect(doc.nodes).toHaveLength(4)
    expect(next.nodes).toHaveLength(5)
    expect(next.nodes[4]).toMatchObject({ type: 'sphere', params: { r: 5 } })
    expect(next.nodes[4].inputs).toBeUndefined()
  })

  it('gives a node with sockets an inputs map', () => {
    expect(G.addNode(makeDoc(), 'union').nodes.at(-1).inputs).toEqual({})
  })

  it('refuses an unknown type', () => {
    expect(() => G.addNode(makeDoc(), 'loft')).toThrow(/Unknown node type/)
  })

  it('removes a node and every reference to it', () => {
    const next = G.removeNode(makeDoc(), 'bore')
    expect(next.nodes.find((n) => n.id === 'bore')).toBeUndefined()
    expect(next.nodes.find((n) => n.id === 'body').inputs).toEqual({ a: 'base' })
  })

  it('drops outputs pointing at a removed node', () => {
    expect(G.removeNode(makeDoc(), 'soft').outputs).toEqual({})
  })

  it('leaves untouched nodes identical when removing', () => {
    const doc = makeDoc()
    const next = G.removeNode(doc, 'soft')
    expect(next.nodes[0]).toBe(doc.nodes[0])
  })

  it('sets a param', () => {
    const next = G.setNodeParam(makeDoc(), 'base', 'w', 99)
    expect(next.nodes[0].params.w).toBe(99)
    expect(next.nodes[0].params.d).toBe(40)
  })

  it('sets a param on a node that had none', () => {
    const doc = { ...makeDoc(), nodes: [{ id: 'b', type: 'box' }], outputs: { p: 'b' } }
    expect(G.setNodeParam(doc, 'b', 'w', 5).nodes[0].params).toEqual({ w: 5 })
  })

  it('connects a valid pair', () => {
    const doc = G.disconnect(makeDoc(), 'soft', 'shape')
    const next = G.connect(doc, 'soft', 'shape', 'base')
    expect(next.nodes.find((n) => n.id === 'soft').inputs.shape).toBe('base')
  })

  it('refuses a connection that would loop', () => {
    expect(() => G.connect(makeDoc(), 'base', 'shape', 'soft')).toThrow(/has no input/)
    const doc = {
      version: '1.0.0',
      nodes: [
        { id: 'a', type: 'box' },
        { id: 'b', type: 'translate', inputs: { shape: 'a' } },
        { id: 'c', type: 'translate', inputs: { shape: 'b' } },
      ],
      outputs: { part: 'c' },
    }
    expect(() => G.connect(doc, 'b', 'shape', 'c')).toThrow(/would create a loop/)
  })

  it('refuses a socket type mismatch', () => {
    const doc = {
      version: '1.0.0',
      nodes: [
        { id: 'b', type: 'box' },
        { id: 'e', type: 'extrude', inputs: {} },
      ],
      outputs: { part: 'e' },
    }
    expect(() => G.connect(doc, 'e', 'profile', 'b')).toThrow(/needs a profile/)
  })

  it('refuses unknown nodes and sockets', () => {
    expect(() => G.connect(makeDoc(), 'ghost', 'shape', 'base')).toThrow(/Unknown node "ghost"/)
    expect(() => G.connect(makeDoc(), 'soft', 'nope', 'base')).toThrow(/has no input "nope"/)
    expect(() => G.connect(makeDoc(), 'soft', 'shape', 'ghost')).toThrow(/Unknown node "ghost"/)
  })

  it('disconnects a socket, and ignores nodes without inputs', () => {
    const next = G.disconnect(makeDoc(), 'soft', 'shape')
    expect(next.nodes.find((n) => n.id === 'soft').inputs).toEqual({})
    expect(G.disconnect(makeDoc(), 'base', 'shape').nodes[0]).toEqual(makeDoc().nodes[0])
  })

  it('sets an output', () => {
    expect(G.setOutput(makeDoc(), 'extra', 'body').outputs).toEqual({ part: 'soft', extra: 'body' })
  })
})

describe('serialization', () => {
  it('round-trips', () => {
    const doc = makeDoc()
    expect(G.parseGraph(G.serializeGraph(doc))).toEqual(doc)
  })

  it('ends the file with a newline', () => {
    expect(G.serializeGraph(makeDoc()).endsWith('\n')).toBe(true)
  })

  it('explains malformed JSON', () => {
    expect(() => G.parseGraph('{nope')).toThrow(/not valid JSON/)
  })

  it('lists every problem, not just the first', () => {
    const doc = makeDoc()
    doc.version = '3.0'
    doc.nodes[3].inputs.shape = 'ghost'
    let message = ''
    try {
      G.parseGraph(JSON.stringify(doc))
    } catch (err) {
      message = err.message
    }
    expect(message).toMatch(/2 problems/)
    expect(message).toMatch(/Version/)
    expect(message).toMatch(/ghost/)
  })

  it('uses the singular for one problem', () => {
    expect(() => G.parseGraph(JSON.stringify({ ...makeDoc(), version: '3.0' }))).toThrow(/1 problem:/)
  })

  it('starts an empty graph that is editable into a valid one', () => {
    const empty = G.emptyGraph()
    expect(G.validateGraph(empty).some((i) => /at least one node/.test(i.message))).toBe(true)
    const built = G.setOutput(G.addNode(empty, 'box', 'plate'), 'part', 'plate')
    expect(G.validateGraph(built)).toEqual([])
  })
})
