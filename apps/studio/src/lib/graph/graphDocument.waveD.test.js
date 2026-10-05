import { describe, it, expect, vi } from 'vitest'

/**
 * The Wave D vocabulary (yantra4d #213, P8-ENGINE): select, reflect,
 * profile_polyline and a bounded revolve; the condition and points kinds; the
 * one-consumer rule for profiles; and the new limits. The specs below are the
 * ones #213's generated catalog carries, so this suite holds before and after
 * that catalog lands (small limits make the limit rules testable).
 */
vi.mock('../../config/graph-node-catalog.json', async (importOriginal) => {
  const catalog = structuredClone((await importOriginal()).default)
  for (const spec of Object.values(catalog.nodes)) {
    for (const param of Object.values(spec.params)) param.expr = param.kind === 'float' || param.kind === 'count'
  }
  Object.assign(catalog.nodes, {
    select: { output: 'solid', inputs: { if_false: 'solid', if_true: 'solid' }, params: { when: { kind: 'condition', default: true, bindable: false, expr: true } } },
    reflect: { output: 'solid', inputs: { shape: 'solid' }, params: { plane: { kind: 'plane', default: 'YZ', bindable: false, expr: false } } },
    profile_polyline: { output: 'profile', inputs: {}, params: {
      plane: { kind: 'plane', default: 'XY', bindable: false, expr: false },
      points: { kind: 'points', default: [[0, 0], [10, 0], [0, 10]], bindable: false, expr: true },
    } },
    revolve: { output: 'solid', inputs: { profile: 'profile' }, params: {
      angle: { kind: 'float', default: 360, bindable: true, expr: true },
      axis: { kind: 'axis', default: 'z', bindable: false, expr: false },
    } },
  })
  Object.assign(catalog.limits, { max_parameters: 3, max_derived: 2, max_map_entries: 2, max_polyline_points: 5, max_revolve_extent_mm: 100 })
  return { default: catalog }
})

const G = await import('./graphDocument')

function ring() {
  return {
    version: '1.1.0',
    parameters: { od: { default: 30 } },
    nodes: [
      { id: 'section', type: 'profile_polyline', params: { plane: 'XZ', points: [[5, 0], [10, 0], [10, { expr: 'od / 3' }]] } },
      { id: 'body', type: 'revolve', inputs: { profile: 'section' }, params: { angle: 360, axis: 'z' } },
    ],
    outputs: { ring: 'body' },
  }
}

describe('Wave D catalog', () => {
  it('reads the new limits from the catalog', () => {
    expect(G.LIMITS.max_polyline_points).toBe(5)
    expect(G.LIMITS.max_revolve_extent_mm).toBe(100)
  })

  it('accepts a polyline with expression coordinates revolved about an in-plane axis', () => {
    expect(G.validateGraph(ring())).toEqual([])
  })

  it('a points param is never a whole expression, only its coordinates', () => {
    expect(G.isExpressible('profile_polyline', 'points')).toBe(false)
    const doc = ring()
    doc.nodes[0].params.points = { expr: 'od' }
    expect(G.validateGraph(doc)[0].message).toMatch(/put expressions on its coordinates/)
  })

  it('checks every expression coordinate, and says which one', () => {
    const doc = ring()
    doc.nodes[0].params.points[2][1] = { expr: 'id / 3' }
    expect(G.validateGraph(doc)).toEqual([
      expect.objectContaining({ nodeId: 'section', param: 'points', message: expect.stringMatching(/point 3 y.*"id"/) }),
    ])
  })

  it('enforces the polyline point count', () => {
    const doc = ring()
    doc.nodes[0].params.points = [[1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0]]
    expect(G.validateGraph(doc)[0].message).toMatch(/3 to 5/)
  })

  it('refuses a revolve axis outside the profile plane', () => {
    const doc = ring()
    doc.nodes[1].params.axis = 'y'
    expect(G.validateGraph(doc)).toEqual([
      expect.objectContaining({ nodeId: 'body', param: 'axis', message: expect.stringMatching(/not in the profile's XZ plane/) }),
    ])
  })

  it('bounds the revolve angle', () => {
    const doc = ring()
    doc.nodes[1].params.angle = 400
    expect(G.validateGraph(doc)[0]).toMatchObject({ nodeId: 'body', param: 'angle' })
    doc.nodes[1].params.angle = 0
    expect(G.validateGraph(doc)[0].message).toMatch(/more than 0/)
  })

  it('bounds how far a literal profile reaches from the origin', () => {
    const doc = ring()
    doc.nodes[0].params.points = [[5, 0], [200, 0], [5, 10]]
    expect(G.validateGraph(doc)[0].message).toMatch(/reaches 200 mm.*100 mm/)
  })

  it('lets a profile feed only one node', () => {
    const doc = ring()
    doc.nodes.push({ id: 'slab', type: 'extrude', inputs: { profile: 'section' }, params: { height: 2 } })
    expect(G.validateGraph(doc)).toEqual([
      expect.objectContaining({ nodeId: 'slab', socket: 'profile', message: expect.stringMatching(/already feeds "body"/) }),
    ])
  })

  it('refuses a second profile consumer before the connection is made', () => {
    let doc = ring()
    doc = G.addNode(doc, 'extrude', 'slab')
    expect(G.connectionProblem(doc, 'slab', 'profile', 'section')).toMatch(/already feeds "body"/)
    expect(() => G.connect(doc, 'slab', 'profile', 'section')).toThrow(/one node/)
    // re-pointing the same consumer is not a second consumer
    expect(G.connectionProblem(doc, 'body', 'profile', 'section')).toBeNull()
  })

  it('a select reads a boolean or an expression, numbers included', () => {
    const doc = {
      version: '1.1.0',
      parameters: { mirrored: { default: false }, count: { default: 2 } },
      nodes: [
        { id: 'a', type: 'box' },
        { id: 'b', type: 'reflect', inputs: { shape: 'a' } },
        { id: 'pick', type: 'select', inputs: { if_true: 'b', if_false: 'a' }, params: { when: { expr: 'mirrored' } } },
      ],
      outputs: { part: 'pick' },
    }
    expect(G.validateGraph(doc)).toEqual([])
    doc.nodes[2].params.when = { expr: 'count - 2' }
    expect(G.validateGraph(doc)).toEqual([])
    doc.nodes[2].params.when = 1
    expect(G.validateGraph(doc)[0].message).toMatch(/true or false/)
  })

  it('enforces the declaration limits', () => {
    const doc = ring()
    doc.parameters = { a: { default: 1 }, b: { default: 1 }, c: { default: 1 }, od: { default: 30 } }
    doc.derived = [{ id: 'x', expr: '1' }, { id: 'y', expr: '1' }, { id: 'z', expr: '1' }]
    doc.parameters.c = { default: 'm', map: { m: 1, n: 2, o: 3 } }
    const messages = G.validateGraph(doc).map((i) => i.message)
    expect(messages).toEqual(expect.arrayContaining([
      'Too many declared parameters: 4 (limit 3).',
      'Too many derived values: 3 (limit 2).',
      'Declared parameter "c" maps 3 options (limit 2).',
    ]))
  })
})
