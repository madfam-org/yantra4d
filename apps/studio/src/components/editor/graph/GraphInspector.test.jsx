import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// The catalog as it reads once the engine marks numeric params expressible.
vi.mock('../../../config/graph-node-catalog.json', async (importOriginal) => {
  const catalog = structuredClone((await importOriginal()).default)
  for (const spec of Object.values(catalog.nodes)) {
    for (const param of Object.values(spec.params)) param.expr = param.kind === 'float' || param.kind === 'count'
  }
  return { default: catalog }
})
vi.mock('../../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({
    t: (key, params) => (params ? `${key}(${Object.values(params).join(',')})` : key),
  }),
}))

const GraphInspector = (await import('./GraphInspector')).default
const { checkExpression } = await import('../../../lib/graph/graphExpressions')

const DOC = {
  version: '1.0.0',
  nodes: [{ id: 'body', type: 'box', params: { w: { expr: 'width / 2' } } }],
  outputs: { part: 'body' },
}
const MANIFEST = [
  { id: 'width', type: 'slider', default: 40 },
  { id: 'nema', type: 'select', default: 'NEMA17', options: [{ value: 'NEMA17' }] },
  { id: 'odd', type: 'slider' },
]

function setup(doc = DOC, node = doc.nodes[0]) {
  const onDocChange = vi.fn()
  render(
    <GraphInspector
      doc={doc}
      node={node}
      issues={[]}
      bindings={{}}
      bindable={[]}
      bindBlockedReason={null}
      manifestParameters={MANIFEST}
      partIds={['part']}
      checkExpression={(expr) => checkExpression(expr, doc.parameters ?? {}, {}, [])}
      onDocChange={onDocChange}
      onBindingsChange={vi.fn()}
      onDelete={vi.fn()}
    />,
  )
  return { onDocChange, last: () => onDocChange.mock.calls[onDocChange.mock.calls.length - 1][0] }
}

describe('GraphInspector expressions', () => {
  it('declares a manifest parameter an expression reads, with its manifest default', () => {
    const { last } = setup()
    fireEvent.click(screen.getByText('graph.declare_parameter(width)'))
    expect(last().parameters).toEqual({ width: { default: 40 } })
    expect(last().version).toBe('1.1.0')
  })

  it('declares a named select with its option as default; the map is the author’s to add', () => {
    const doc = { ...DOC, nodes: [{ id: 'body', type: 'box', params: { w: { expr: 'nema * 2' } } }] }
    const { last } = setup(doc)
    fireEvent.click(screen.getByText('graph.declare_parameter(nema)'))
    expect(last().parameters).toEqual({ nema: { default: 'NEMA17' } })
  })

  it('falls back to 0 for a manifest parameter with no default', () => {
    const doc = { ...DOC, nodes: [{ id: 'body', type: 'box', params: { w: { expr: 'odd' } } }] }
    const { last } = setup(doc)
    fireEvent.click(screen.getByText('graph.declare_parameter(odd)'))
    expect(last().parameters).toEqual({ odd: { default: 0 } })
  })

  it('writes an expression as the author types', () => {
    const { last } = setup()
    fireEvent.change(screen.getByTestId('graph-expr-body-w'), { target: { value: 'width / 4' } })
    expect(last().nodes[0].params.w).toEqual({ expr: 'width / 4' })
  })
})

describe('GraphInspector edge cases', () => {
  it('says so when a node type is not in the catalog', () => {
    const node = { id: 'mystery', type: 'teleport' }
    setup({ ...DOC, nodes: [node] }, node)
    expect(screen.getByText('graph.unknown_type(teleport)')).toBeInTheDocument()
  })

  it('shows node-level issues', () => {
    const onDocChange = vi.fn()
    render(
      <GraphInspector doc={DOC} node={DOC.nodes[0]} issues={[{ message: 'Duplicate node id "body".', nodeId: 'body' }]}
        bindings={{}} bindable={[]} bindBlockedReason={null} manifestParameters={[]} partIds={[]}
        checkExpression={() => ({ undeclared: [] })} onDocChange={onDocChange} onBindingsChange={vi.fn()} onDelete={vi.fn()} />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Duplicate node id')
  })

  it('ignores an empty part id', () => {
    const { onDocChange } = setup()
    fireEvent.click(screen.getByText('graph.set_output'))
    fireEvent.keyDown(screen.getByLabelText('graph.output_part_id'), { key: 'Enter' })
    expect(onDocChange).not.toHaveBeenCalled()
  })
})
