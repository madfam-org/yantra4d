import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, within, act } from '@testing-library/react'
import { axe } from '../../test/axe-setup'
import { toHaveNoViolations } from 'jest-axe'

expect.extend(toHaveNoViolations)

// React Flow needs a real layout engine; this stand-in renders the node cards
// through the canvas's own nodeTypes and keeps the props it was given, so a
// test can check what the canvas allows (nothing that edits) and click a node.
const rf = vi.hoisted(() => ({ props: null, applied: [] }))
vi.mock('@xyflow/react', () => ({
  ReactFlow: (props) => {
    rf.props = props
    const { nodes, edges, nodeTypes } = props
    return (
      <div data-testid="rf" data-edges={edges.map((e) => e.id).join('|')}>
        {nodes.map((n) => {
          const Card = nodeTypes[n.type]
          return (
            <button type="button" key={n.id} data-testid={`rf-node-${n.id}`} onClick={(e) => props.onNodeClick?.(e, n)}>
              <Card id={n.id} data={n.data} selected={!!n.selected} />
            </button>
          )
        })}
        {props.children}
      </div>
    )
  },
  ReactFlowProvider: ({ children }) => children,
  applyNodeChanges: (changes, nodes) => { rf.applied.push(...changes); return nodes },
  Handle: ({ type, id }) => <span data-testid={`handle-${type}-${id}`} />,
  Position: { Left: 'left', Right: 'right' },
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
}))
vi.mock('@xyflow/react/dist/style.css', () => ({}))
vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({
    t: (key, params) => (params ? `${key}(${Object.values(params).join(',')})` : key),
  }),
}))
vi.mock('../../contexts/system/ThemeProvider', () => ({ useTheme: () => ({ theme: 'light' }) }))

const InsidePanel = (await import('./InsidePanel')).default

const FLANGE = {
  version: '1.0.0',
  nodes: [
    { id: 'outline', type: 'profile_circle', params: { r: 45 } },
    { id: 'plate', type: 'extrude', inputs: { profile: 'outline' }, params: { height: 8 } },
    { id: 'bore', type: 'cylinder', params: { r: 12, h: 400 } },
    { id: 'drilled', type: 'cut', inputs: { a: 'plate', b: 'bore' } },
  ],
  outputs: { flange: 'drilled' },
}
const ready = (doc = FLANGE, extra = {}) => ({
  status: 'ready', error: null,
  graph: { mode: 'flange', path: 'flange.graph.json', role: 'source', script: null, content: JSON.stringify(doc), ...extra },
})
const BINDINGS = { plate_radius: ['outline.r'], thickness: ['plate.height'] }
const LABELS = { plate_radius: 'Plate radius', thickness: 'Thickness' }

function renderPanel(props = {}) {
  return render(
    <InsidePanel
      state={ready()}
      onRetry={vi.fn()}
      bindings={BINDINGS}
      values={{ plate_radius: 50, thickness: 8 }}
      labelOf={(id) => LABELS[id] ?? id}
      activeParamId={null}
      {...props}
    />,
  )
}

beforeEach(() => { rf.props = null; rf.applied = [] })

describe('InsidePanel: the graph, read-only', () => {
  it('draws every node and every wire', () => {
    renderPanel()
    for (const id of ['outline', 'plate', 'bore', 'drilled']) expect(screen.getByTestId(`rf-node-${id}`)).toBeInTheDocument()
    expect(screen.getByTestId('rf').dataset.edges.split('|').sort()).toEqual(['bore->drilled.b', 'outline->plate.profile', 'plate->drilled.a'])
  })

  it('allows nothing that would edit the document', () => {
    renderPanel()
    expect(rf.props.nodesDraggable).toBe(false)
    expect(rf.props.nodesConnectable).toBe(false)
    expect(rf.props.deleteKeyCode).toBeNull()
    expect(rf.props.onConnect).toBeUndefined()
    expect(rf.props.onEdgesChange).toBeUndefined()
    expect(rf.props.onNodeDragStop).toBeUndefined()
    expect(rf.props.nodes.every((n) => n.draggable === false && n.connectable === false && n.deletable === false)).toBe(true)
    expect(screen.queryByText('graph.save')).toBeNull()
    expect(screen.queryByText('graph.palette')).toBeNull()
  })

  it('says how many nodes, that the graph builds the view, and that it is read-only', () => {
    renderPanel()
    expect(screen.getByTestId('inside-summary')).toHaveTextContent('inside.node_count(4) · inside.role_source · inside.read_only')
  })

  it('names the script a twin stands beside', () => {
    renderPanel({ state: ready(FLANGE, { role: 'twin', script: 'main.py' }) })
    expect(screen.getByTestId('inside-summary')).toHaveTextContent('inside.role_twin(main.py)')
  })

  it('uses the singular for one node', () => {
    renderPanel({ state: ready({ ...FLANGE, nodes: [FLANGE.nodes[0]] }) })
    expect(screen.getByTestId('inside-summary')).toHaveTextContent('inside.node_count_one(1)')
  })
})

describe('InsidePanel: React Flow changes', () => {
  it('applies measurements only: a move, a removal or a selection from React Flow changes nothing', () => {
    renderPanel()
    act(() => {
      rf.props.onNodesChange([
        { type: 'position', id: 'bore', position: { x: 999, y: 0 } },
        { type: 'remove', id: 'bore' },
        { type: 'select', id: 'bore', selected: true },
      ])
    })
    expect(rf.applied).toEqual([])
    expect(screen.getByTestId('rf-node-bore')).toBeInTheDocument()
    expect(screen.getByText('inside.select_hint')).toBeInTheDocument()
    act(() => { rf.props.onNodesChange([{ type: 'dimensions', id: 'bore', dimensions: { width: 150, height: 60 } }]) })
    expect(rf.applied.map((c) => c.type)).toEqual(['dimensions'])
  })

  it('keeps measured sizes when a hover mark changes the node set', () => {
    const { rerender } = renderPanel()
    const measured = rf.props.nodes.map((n) => ({ ...n, measured: { width: 150, height: 60 } }))
    // Simulate React Flow having measured every node, then a hover mark arriving.
    act(() => { rf.props.onNodesChange(measured.map((n) => ({ type: 'dimensions', id: n.id, dimensions: n.measured }))) })
    rerender(
      <InsidePanel state={ready()} onRetry={vi.fn()} bindings={BINDINGS} values={{}} labelOf={(id) => id} activeParamId="plate_radius" />,
    )
    expect(rf.props.nodes.find((n) => n.id === 'outline').data.highlighted).toBe(true)
  })
})

describe('InsidePanel: selecting a node shows what drives its inputs', () => {
  it('shows a hint until a node is selected', () => {
    renderPanel()
    expect(screen.getByText('inside.select_hint')).toBeInTheDocument()
  })

  it('shows a bound input with its slider label and current value', () => {
    renderPanel()
    fireEvent.click(screen.getByTestId('rf-node-outline'))
    const row = screen.getByTestId('inside-param-r')
    expect(row.dataset.source).toBe('bound')
    expect(row).toHaveTextContent('inside.source_bound(Plate radius)50')
  })

  it('shows a literal and a node default', () => {
    renderPanel()
    fireEvent.click(screen.getByTestId('rf-node-bore'))
    expect(screen.getByTestId('inside-param-h')).toHaveTextContent('400inside.source_literal')
    fireEvent.click(screen.getByTestId('rf-node-outline'))
    expect(screen.getByTestId('inside-param-plane')).toHaveTextContent('XYinside.source_default')
  })

  it('shows an expression and the sliders it reads', () => {
    const doc = {
      version: '1.1.0',
      parameters: { plate_radius: { default: 45 } },
      nodes: [{ id: 'outline', type: 'profile_circle', params: { r: { expr: 'plate_radius / 2' } } }],
      outputs: { flange: 'outline' },
    }
    renderPanel({ state: ready(doc), bindings: {} })
    fireEvent.click(screen.getByTestId('rf-node-outline'))
    expect(screen.getByTestId('inside-param-r')).toHaveTextContent('plate_radius / 2inside.source_reads(Plate radius)')
  })

  it('lists wired inputs and follows one to its node', () => {
    renderPanel()
    fireEvent.click(screen.getByTestId('rf-node-drilled'))
    const details = screen.getByTestId('inside-node-details')
    fireEvent.click(within(details).getByText('inside.from_node(plate)'))
    expect(screen.getByTestId('inside-node-details')).toHaveTextContent('plate')
    expect(screen.getByTestId('inside-param-height')).toBeInTheDocument()
  })

  it('clicking the selected node again clears the selection', () => {
    renderPanel()
    fireEvent.click(screen.getByTestId('rf-node-bore'))
    fireEvent.click(screen.getByTestId('rf-node-bore'))
    expect(screen.getByText('inside.select_hint')).toBeInTheDocument()
  })
})

describe('InsidePanel: the link to the sliders', () => {
  it('marks the nodes the active parameter drives, and only those', () => {
    renderPanel({ activeParamId: 'plate_radius' })
    expect(screen.getByTestId('graph-node-outline').dataset.highlighted).toBe('true')
    expect(screen.getByTestId('graph-node-plate').dataset.highlighted).toBe('false')
    expect(screen.getByTestId('inside-link')).toHaveTextContent('inside.drives_one(Plate radius,1)')
  })

  it('says so when the active parameter drives nothing here', () => {
    renderPanel({ activeParamId: 'colour' })
    expect(screen.getByTestId('inside-link')).toHaveTextContent('inside.drives_none(colour)')
    expect(screen.getAllByTestId(/^graph-node-/).every((n) => n.dataset.highlighted === 'false')).toBe(true)
  })

  it('marks the driven input in the selected node', () => {
    renderPanel({ activeParamId: 'thickness' })
    fireEvent.click(screen.getByTestId('rf-node-plate'))
    expect(screen.getByTestId('inside-param-height').dataset.active).toBe('true')
  })

  it('shows the hint when no slider is active', () => {
    renderPanel()
    expect(screen.getByTestId('inside-link')).toHaveTextContent('inside.link_hint')
  })
})

describe('InsidePanel: the list reading', () => {
  it('lists the nodes in build order and selects from the list', () => {
    renderPanel({ activeParamId: 'plate_radius' })
    fireEvent.click(screen.getByRole('radio', { name: /inside.layout_list/ }))
    const list = screen.getByTestId('inside-node-list')
    const buttons = within(list).getAllByRole('button')
    expect(buttons.map((b) => b.querySelector('.font-semibold').textContent)).toEqual(['outline', 'bore', 'plate', 'drilled'])
    expect(buttons[0].dataset.highlighted).toBe('true')
    fireEvent.click(buttons[3])
    expect(buttons[3]).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('inside-node-details')).toHaveTextContent('drilled')
  })
})

describe('InsidePanel: states', () => {
  it('loading', () => {
    renderPanel({ state: { status: 'loading', graph: null, error: null } })
    expect(screen.getByRole('status')).toHaveTextContent('inside.loading')
  })

  it('error offers a retry', () => {
    const onRetry = vi.fn()
    renderPanel({ state: { status: 'error', graph: null, error: new Error('x') }, onRetry })
    expect(screen.getByRole('alert')).toHaveTextContent('inside.error')
    fireEvent.click(screen.getByRole('button', { name: /inside.retry/ }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('an unreadable document says so instead of drawing nothing', () => {
    renderPanel({ state: { status: 'ready', error: null, graph: { mode: 'm', path: 'g.graph.json', role: 'source', script: null, content: 'nope' } } })
    expect(screen.getByText('inside.unreadable')).toBeInTheDocument()
    expect(screen.queryByTestId('rf')).toBeNull()
  })
})

describe('InsidePanel: accessibility', () => {
  it('has no axe violations with a node selected, in both layouts', async () => {
    const { container } = renderPanel({ activeParamId: 'plate_radius' })
    fireEvent.click(screen.getByTestId('rf-node-outline'))
    expect(await axe(container)).toHaveNoViolations()
    fireEvent.click(screen.getByRole('radio', { name: /inside.layout_list/ }))
    expect(await axe(container)).toHaveNoViolations()
  })
})
