import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

// ReactFlow needs a real layout engine and ResizeObserver; in jsdom it renders
// nothing useful. Mock it to expose the nodes and edges the component computed,
// which is the part worth testing — the layout and the document→graph mapping.
vi.mock('@xyflow/react', () => ({
  ReactFlow: ({ nodes, edges, children }) => (
    <div
      data-testid="rf"
      data-nodes={nodes.map((n) => `${n.id}@${n.position.x},${n.position.y}`).join('|')}
      data-edges={edges.map((e) => e.id).join('|')}
      data-labels={edges.map((e) => e.label).join('|')}
      data-styles={nodes.map((n) => `${n.id}:${n.style.border.includes('dashed') ? 'profile' : 'solid'}`).join('|')}
    >
      {nodes.map((n) => (
        <div key={n.id} data-testid={`rf-node-${n.id}`}>{n.data.label}</div>
      ))}
      {children}
    </div>
  ),
  Background: () => <div data-testid="rf-bg" />,
  Controls: () => <div data-testid="rf-controls" />,
  MiniMap: () => <div data-testid="rf-minimap" />,
}))
vi.mock('@xyflow/react/dist/style.css', () => ({}))

const GraphCanvas = (await import('./GraphCanvas')).default

const chain = {
  version: '1.0.0',
  nodes: [
    { id: 'base', type: 'box', params: { w: 40, d: 20, h: 8 } },
    { id: 'bore', type: 'cylinder', params: { r: 3, h: 40 } },
    { id: 'body', type: 'cut', inputs: { a: 'base', b: 'bore' } },
  ],
  outputs: { part: 'body' },
}

const json = (d) => JSON.stringify(d)
const attr = (name) => screen.getByTestId('rf').getAttribute(name)

describe('GraphCanvas', () => {
  it('explains itself instead of rendering when the document is invalid', () => {
    const broken = structuredClone(chain)
    broken.nodes[2].inputs.b = 'ghost'
    render(<GraphCanvas content={json(broken)} />)
    expect(screen.queryByTestId('rf')).not.toBeInTheDocument()
    expect(screen.getByText(/appears once the document is valid/)).toBeInTheDocument()
  })

  it('renders nothing for unparseable content rather than throwing', () => {
    render(<GraphCanvas content="{nope" />)
    expect(screen.getByText(/appears once the document is valid/)).toBeInTheDocument()
  })

  it('places sources in the first column and consumers to their right', () => {
    render(<GraphCanvas content={json(chain)} />)
    const placed = Object.fromEntries(
      attr('data-nodes').split('|').map((s) => {
        const [id, pos] = s.split('@')
        return [id, pos.split(',').map(Number)]
      }),
    )
    expect(placed.base[0]).toBe(0)
    expect(placed.bore[0]).toBe(0)
    expect(placed.body[0]).toBeGreaterThan(placed.base[0])
  })

  it('stacks nodes that share a column', () => {
    render(<GraphCanvas content={json(chain)} />)
    const rows = attr('data-nodes')
      .split('|')
      .filter((s) => s.includes('@0,'))
      .map((s) => Number(s.split(',')[1]))
    expect(new Set(rows).size).toBe(rows.length)
  })

  it('draws one edge per input socket, labelled with the socket', () => {
    render(<GraphCanvas content={json(chain)} />)
    expect(attr('data-edges').split('|').sort()).toEqual(['base->body.a', 'bore->body.b'])
    expect(attr('data-labels').split('|').sort()).toEqual(['a', 'b'])
  })

  it('distinguishes profiles from solids', () => {
    const withProfile = {
      version: '1.0.0',
      nodes: [
        { id: 'outline', type: 'profile_rect', params: { w: 10, d: 10 } },
        { id: 'solid', type: 'extrude', inputs: { profile: 'outline' }, params: { height: 4 } },
      ],
      outputs: { part: 'solid' },
    }
    render(<GraphCanvas content={json(withProfile)} />)
    const styles = Object.fromEntries(attr('data-styles').split('|').map((s) => s.split(':')))
    expect(styles.outline).toBe('profile')
    expect(styles.solid).toBe('solid')
  })

  it('marks which node produces which part', () => {
    render(<GraphCanvas content={json(chain)} />)
    expect(screen.getByText(/▸ part/)).toBeInTheDocument()
  })

  it('mounts the background, controls and minimap', () => {
    render(<GraphCanvas content={json(chain)} />)
    expect(screen.getByTestId('rf-bg')).toBeInTheDocument()
    expect(screen.getByTestId('rf-controls')).toBeInTheDocument()
    expect(screen.getByTestId('rf-minimap')).toBeInTheDocument()
  })
})
