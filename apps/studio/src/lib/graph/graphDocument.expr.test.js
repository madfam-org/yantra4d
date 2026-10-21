import { describe, it, expect, vi } from 'vitest'

/**
 * G-EXPR against a catalog that declares expressible params. The committed
 * catalog gains `"expr": true` with the engine's G-EXPR change; this suite
 * pins what the editor does once it does, without waiting for it.
 */
vi.mock('../../config/graph-node-catalog.json', async (importOriginal) => {
  const original = (await importOriginal()).default
  const catalog = structuredClone(original)
  for (const spec of Object.values(catalog.nodes)) {
    for (const param of Object.values(spec.params)) param.expr = param.kind === 'float' || param.kind === 'count'
  }
  catalog.expression = { dialect: 'safeFormula', max_length: 64, max_tokens: 128 }
  return { default: catalog }
})

const G = await import('./graphDocument')

function doc() {
  return {
    version: '1.1.0',
    units: 'mm',
    parameters: { width: { default: 40 }, wall: { default: 2 } },
    derived: [{ id: 'inner', expr: 'width - 2 * wall' }],
    nodes: [{ id: 'body', type: 'box', params: { w: { expr: 'inner / 2' }, d: 10, h: 10 } }],
    outputs: { part: 'body' },
  }
}

describe('expression-valued params', () => {
  it('reads the catalog expression block', () => {
    expect(G.EXPRESSION_LIMITS.max_length).toBe(64)
    expect(G.isExpressible('box', 'w')).toBe(true)
    expect(G.isExpressible('chamfer', 'edges')).toBe(false)
  })

  it('accepts an expression over declared parameters and derived values', () => {
    expect(G.validateGraph(doc())).toEqual([])
  })

  it('refuses an identifier the graph has not declared', () => {
    const d = doc()
    d.nodes[0].params.w = { expr: 'height / 2' }
    expect(G.validateGraph(d)).toContainEqual(
      { message: '"w": reads "height", which is not declared.', nodeId: 'body', param: 'w' },
    )
  })

  it('refuses an expression that gives a boolean for a number', () => {
    const d = doc()
    d.nodes[0].params.w = { expr: 'width > 10' }
    expect(G.validateGraph(d)[0].message).toMatch(/true\/false/)
  })

  it('refuses an expression the evaluator rejects', () => {
    const d = doc()
    d.nodes[0].params.w = { expr: 'width / (wall - 2)' }
    expect(G.validateGraph(d)[0]).toMatchObject({ nodeId: 'body', param: 'w' })
  })

  it('enforces the catalog length limit', () => {
    const d = doc()
    d.nodes[0].params.w = { expr: `width${' + 1'.repeat(30)}` }
    expect(G.validateGraph(d)[0].message).toMatch(/longer than 64/)
  })

  it('still refuses an expression on a structural param', () => {
    const d = doc()
    d.nodes.push({ id: 'soft', type: 'chamfer', inputs: { shape: 'body' }, params: { edges: { expr: '1' } } })
    d.outputs = { part: 'soft' }
    expect(G.validateGraph(d)).toEqual([
      { message: '"edges" does not accept an expression.', nodeId: 'soft', param: 'edges' },
    ])
  })
})
