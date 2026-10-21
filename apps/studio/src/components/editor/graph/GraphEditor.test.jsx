import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act, createEvent } from '@testing-library/react'
import { useState } from 'react'

// React Flow needs a real layout engine; in jsdom it renders nothing useful.
// This stand-in renders the node cards through the editor's own nodeTypes and
// keeps the latest props, so a test can fire exactly what React Flow would:
// a connection, a deletion, a drag stop.
const rf = vi.hoisted(() => ({ props: null }))
vi.mock('@xyflow/react', () => ({
  ReactFlow: (props) => {
    rf.props = props
    const { nodes, edges, nodeTypes } = props
    return (
      <div data-testid="rf" data-edges={edges.map((e) => e.id).join('|')}>
        {nodes.map((n) => {
          const Card = nodeTypes[n.type]
          return (
            <div key={n.id} data-testid={`rf-node-${n.id}`} data-x={n.position.x} data-y={n.position.y}>
              <Card id={n.id} data={n.data} selected={!!n.selected} />
            </div>
          )
        })}
        {props.children}
      </div>
    )
  },
  ReactFlowProvider: ({ children }) => children,
  useReactFlow: () => ({ screenToFlowPosition: (p) => ({ x: p.x, y: p.y }) }),
  applyNodeChanges: (_changes, nodes) => nodes,
  Handle: ({ type, id }) => <span data-testid={`handle-${type}-${id}`} />,
  Position: { Left: 'left', Right: 'right' },
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
}))
vi.mock('@xyflow/react/dist/style.css', () => ({}))
vi.mock('../../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({
    t: (key, params) => (params ? `${key}(${Object.values(params).join(',')})` : key),
  }),
}))
vi.mock('../../../contexts/system/ThemeProvider', () => ({ useTheme: () => ({ theme: 'dark' }) }))

const GraphEditor = (await import('./GraphEditor')).default

const FLANGE = {
  version: '1.0.0',
  units: 'mm',
  nodes: [
    { id: 'outline', type: 'profile_circle', params: { r: 45 } },
    { id: 'plate', type: 'extrude', inputs: { profile: 'outline' }, params: { height: 8 } },
    { id: 'bore', type: 'cylinder', params: { r: 12, h: 40 } },
    { id: 'drilled', type: 'cut', inputs: { a: 'plate', b: 'bore' } },
  ],
  outputs: { flange: 'drilled' },
}
const json = (d) => `${JSON.stringify(d, null, 2)}\n`
const MANIFEST_PARAMS = [
  { id: 'plate_radius', type: 'slider', default: 45 },
  { id: 'bore_radius', type: 'slider', default: 12 },
]

/** Holds the buffer the way ScadEditor does, so successive edits compose. */
function Harness({ initial = FLANGE, spy, onBindingsChange = vi.fn(), bindings = { plate_radius: ['outline.r'] }, ...rest }) {
  const [content, setContent] = useState(typeof initial === 'string' ? initial : json(initial))
  const [selectedId, setSelectedId] = useState(null)
  return (
    <GraphEditor
      content={content}
      fileName="flange.graph.json"
      onDocumentChange={(next, opts) => { spy?.(next, opts); setContent(next) }}
      manifestParameters={MANIFEST_PARAMS}
      partIds={['flange', 'blank']}
      bindings={bindings}
      bindable={MANIFEST_PARAMS}
      onBindingsChange={onBindingsChange}
      bindBlockedReason={null}
      saveBlockedReason={null}
      saveStatus="clean"
      onSave={vi.fn()}
      selectedId={selectedId}
      onSelect={setSelectedId}
      {...rest}
    />
  )
}

/** What React Flow reports when a node is clicked. */
const selectNode = (id) => act(() => rf.props.onNodesChange([{ type: 'select', id, selected: true }]))
const lastDoc = (spy) => JSON.parse(spy.mock.calls[spy.mock.calls.length - 1][0])
const lastOpts = (spy) => spy.mock.calls[spy.mock.calls.length - 1][1]

beforeEach(() => {
  rf.props = null
})

describe('GraphEditor canvas', () => {
  it('draws a card per node with a handle per input socket and one output', () => {
    render(<Harness />)
    expect(screen.getByTestId('graph-node-drilled')).toBeInTheDocument()
    expect(screen.getByTestId('handle-target-a')).toBeInTheDocument()
    expect(screen.getByTestId('handle-target-b')).toBeInTheDocument()
    expect(screen.getAllByTestId('handle-source-out')).toHaveLength(4)
    expect(screen.getByTestId('rf').dataset.edges.split('|').sort()).toEqual([
      'bore->drilled.b', 'outline->plate.profile', 'plate->drilled.a',
    ])
    // the part a node outputs and the params a manifest parameter drives are on the card
    expect(screen.getByTestId('graph-node-drilled')).toHaveTextContent('▸ flange')
    expect(screen.getByTestId('graph-node-outline')).toHaveTextContent('⇠ r')
  })

  it('lays out by dependency depth when nothing is stored', () => {
    render(<Harness />)
    expect(Number(screen.getByTestId('rf-node-outline').dataset.x)).toBe(0)
    expect(Number(screen.getByTestId('rf-node-drilled').dataset.x)).toBeGreaterThan(Number(screen.getByTestId('rf-node-plate').dataset.x))
  })

  it('marks a node the validator found a problem on, and the socket', () => {
    const broken = structuredClone(FLANGE)
    delete broken.nodes[3].inputs.b
    render(<Harness initial={broken} />)
    expect(screen.getByTestId('graph-node-drilled').dataset.hasIssue).toBe('true')
    expect(screen.getByTestId('graph-node-plate').dataset.hasIssue).toBe('false')
    expect(screen.getByTestId('graph-socket-drilled-b').querySelector('.text-destructive')).not.toBeNull()
  })

  it('marks a param that is both bound and an expression', () => {
    const doc = structuredClone(FLANGE)
    doc.version = '1.1.0'
    doc.parameters = { plate_radius: { default: 45 } }
    doc.nodes[0].params.r = { expr: 'plate_radius' }
    render(<Harness initial={doc} />)
    expect(screen.getByTestId('graph-node-outline').dataset.hasIssue).toBe('true')
  })

  it('explains itself when the buffer is not a graph', () => {
    render(<Harness initial="{nope" />)
    expect(screen.getByText('graph.unparseable')).toBeInTheDocument()
    expect(screen.queryByTestId('rf')).not.toBeInTheDocument()
  })

  it('refuses nodes without ids rather than drawing them', () => {
    render(<Harness initial={JSON.stringify({ nodes: [{ type: 'box' }] })} />)
    expect(screen.getByText('graph.unparseable')).toBeInTheDocument()
  })

  it('opens the palette on an empty graph and closes it otherwise', () => {
    const { unmount } = render(<Harness initial={{ version: '1.0.0', nodes: [], outputs: {} }} />)
    expect(screen.getByTestId('graph-palette')).toBeInTheDocument()
    expect(screen.getByText('graph.empty')).toBeInTheDocument()
    unmount()
    render(<Harness />)
    expect(screen.queryByTestId('graph-palette')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /graph.palette/ }))
    expect(screen.getByTestId('graph-palette')).toBeInTheDocument()
  })
})

describe('GraphEditor edits', () => {
  it('adds a node from the palette below the others and selects it', () => {
    const spy = vi.fn()
    render(<Harness spy={spy} />)
    fireEvent.click(screen.getByRole('button', { name: /graph.palette/ }))
    fireEvent.click(screen.getByTestId('graph-palette-sphere'))
    const doc = lastDoc(spy)
    const added = doc.nodes.find((n) => n.id === 'sphere_1')
    expect(added).toMatchObject({ type: 'sphere', params: { r: expect.any(Number) } })
    expect(added.meta.position.y).toBeGreaterThan(0)
    expect(lastOpts(spy)).toEqual({ layoutOnly: false })
    expect(screen.getByTestId('graph-inspector')).toHaveTextContent('sphere_1')
  })

  it('filters the palette', () => {
    render(<Harness initial={{ version: '1.0.0', nodes: [], outputs: {} }} />)
    fireEvent.change(screen.getByLabelText('graph.palette_filter'), { target: { value: 'profile' } })
    expect(screen.getByTestId('graph-palette-profile_rect')).toBeInTheDocument()
    expect(screen.queryByTestId('graph-palette-box')).not.toBeInTheDocument()
  })

  it('adds a node dropped from the palette where it was dropped', () => {
    const spy = vi.fn()
    render(<Harness spy={spy} />)
    const dataTransfer = { getData: (t) => (t === 'application/x-yantra4d-graph-node' ? 'box' : ''), types: ['application/x-yantra4d-graph-node'] }
    fireEvent.dragOver(screen.getByTestId('graph-canvas'), { dataTransfer: { ...dataTransfer, dropEffect: '' } })
    const canvas = screen.getByTestId('graph-canvas')
    const drop = createEvent.drop(canvas, { dataTransfer })
    Object.defineProperties(drop, { clientX: { value: 300 }, clientY: { value: 120 } })
    fireEvent(canvas, drop)
    expect(lastDoc(spy).nodes.find((n) => n.id === 'box_1').meta.position).toEqual({ x: 300, y: 120 })
  })

  it('ignores a drop that is not a palette node', () => {
    const spy = vi.fn()
    render(<Harness spy={spy} />)
    fireEvent.drop(screen.getByTestId('graph-canvas'), { dataTransfer: { getData: () => 'not-a-node', types: [] } })
    expect(spy).not.toHaveBeenCalled()
  })

  it('connects through the model, and refuses a socket type mismatch', () => {
    const spy = vi.fn()
    const loose = structuredClone(FLANGE)
    delete loose.nodes[3].inputs.b
    render(<Harness initial={loose} spy={spy} />)
    const valid = { source: 'bore', target: 'drilled', targetHandle: 'b', sourceHandle: 'out' }
    const wrongType = { source: 'outline', target: 'drilled', targetHandle: 'b', sourceHandle: 'out' }
    expect(rf.props.isValidConnection(valid)).toBe(true)
    expect(rf.props.isValidConnection(wrongType)).toBe(false)
    expect(rf.props.isValidConnection({ ...valid, targetHandle: null })).toBe(false)

    act(() => rf.props.onConnect(wrongType))
    expect(spy).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent(/needs a solid/)
    fireEvent.click(screen.getByText('graph.dismiss'))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()

    act(() => rf.props.onConnect(valid))
    expect(lastDoc(spy).nodes[3].inputs).toEqual({ a: 'plate', b: 'bore' })
  })

  it('refuses a connection that would make a loop', () => {
    render(<Harness />)
    expect(rf.props.isValidConnection({ source: 'drilled', target: 'plate', targetHandle: 'profile' })).toBe(false)
  })

  it('removing an edge disconnects that socket', () => {
    const spy = vi.fn()
    render(<Harness spy={spy} />)
    act(() => rf.props.onEdgesChange([{ type: 'select', id: 'bore->drilled.b' }]))
    expect(spy).not.toHaveBeenCalled()
    act(() => rf.props.onEdgesChange([{ type: 'remove', id: 'bore->drilled.b' }]))
    expect(lastDoc(spy).nodes[3].inputs).toEqual({ a: 'plate' })
  })

  it('deleting a bound node drops its bindings in the same edit', () => {
    const spy = vi.fn()
    render(<Harness spy={spy} />)
    act(() => rf.props.onNodesDelete([{ id: 'outline' }]))
    expect(lastDoc(spy).nodes.map((n) => n.id)).not.toContain('outline')
    expect(lastOpts(spy)).toEqual({ layoutOnly: false, bindings: {} })
  })

  it('deleting an unbound node leaves the bindings alone', () => {
    const spy = vi.fn()
    render(<Harness spy={spy} />)
    act(() => rf.props.onNodesDelete([{ id: 'bore' }]))
    expect(lastOpts(spy)).toEqual({ layoutOnly: false })
  })

  it('a drag stores positions as a layout-only change', () => {
    const spy = vi.fn()
    render(<Harness spy={spy} />)
    act(() => rf.props.onNodeDragStop({}, { id: 'bore' }, [{ id: 'bore', position: { x: 512.4, y: 77.7 } }]))
    expect(lastDoc(spy).nodes[2].meta).toEqual({ position: { x: 512, y: 78 } })
    expect(lastOpts(spy)).toEqual({ layoutOnly: true })
  })

  it('selecting another node wins whichever order React Flow reports the two changes in', () => {
    render(<Harness />)
    selectNode('bore')
    act(() => rf.props.onNodesChange([
      { type: 'select', id: 'plate', selected: true },
      { type: 'select', id: 'bore', selected: false },
    ]))
    expect(screen.getByTestId('graph-inspector')).toHaveTextContent('plate')
    act(() => rf.props.onNodesChange([
      { type: 'select', id: 'plate', selected: false },
      { type: 'select', id: 'outline', selected: true },
    ]))
    expect(screen.getByTestId('graph-inspector')).toHaveTextContent('outline')
  })

  it('selects on click and deselects on the pane', () => {
    render(<Harness />)
    selectNode('bore')
    expect(screen.getByTestId('graph-inspector')).toHaveTextContent('bore')
    act(() => rf.props.onNodesChange([{ type: 'select', id: 'bore', selected: false }]))
    expect(screen.queryByTestId('graph-inspector')).not.toBeInTheDocument()
    selectNode('bore')
    act(() => rf.props.onPaneClick())
    expect(screen.getByText('graph.select_hint')).toBeInTheDocument()
  })
})

describe('GraphEditor inspector', () => {
  function select(id, props = {}) {
    const spy = vi.fn()
    const onBindingsChange = vi.fn()
    render(<Harness spy={spy} onBindingsChange={onBindingsChange} {...props} />)
    selectNode(id)
    return { spy, onBindingsChange }
  }

  it('edits a literal and resets it to the catalog default', () => {
    const { spy } = select('bore')
    fireEvent.change(screen.getByLabelText('graph.param_value(h)'), { target: { value: '55' } })
    expect(lastDoc(spy).nodes[2].params.h).toBe(55)
    fireEvent.click(screen.getAllByText('graph.reset_default')[0])
    expect(lastDoc(spy).nodes[2].params).not.toHaveProperty('h')
  })

  it('binds a param to a manifest parameter', () => {
    const { onBindingsChange } = select('bore')
    fireEvent.change(screen.getByLabelText('graph.param_mode(r)'), { target: { value: 'bound' } })
    // the first bindable manifest parameter is offered first; one driver per node param
    expect(onBindingsChange).toHaveBeenCalledWith({ plate_radius: ['outline.r', 'bore.r'] })
  })

  it('disconnects a socket and deletes the node', () => {
    const { spy } = select('drilled')
    fireEvent.click(screen.getByLabelText('graph.disconnect(b)'))
    expect(lastDoc(spy).nodes[3].inputs).toEqual({ a: 'plate' })
    fireEvent.click(screen.getByLabelText('graph.delete_node(drilled)'))
    expect(lastDoc(spy).nodes.map((n) => n.id)).not.toContain('drilled')
    expect(lastDoc(spy).outputs).toEqual({})
  })

  it('sets and removes the part a solid outputs', () => {
    const { spy } = select('plate')
    const input = screen.getByLabelText('graph.output_part_id')
    fireEvent.change(input, { target: { value: 'blank' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(lastDoc(spy).outputs).toEqual({ flange: 'drilled', blank: 'plate' })
    fireEvent.click(screen.getByText('graph.remove_output'))
    expect(lastDoc(spy).outputs).toEqual({ flange: 'drilled' })
  })

  it('offers no output part on a profile', () => {
    select('outline')
    expect(screen.queryByLabelText('graph.output_part_id')).not.toBeInTheDocument()
  })

  it('says why bindings are unavailable on a project that is not a fork', () => {
    select('bore', { bindBlockedReason: 'graph.bind_blocked_not_fork' })
    expect(screen.getByText('graph.bind_blocked_not_fork')).toBeInTheDocument()
    const option = screen.getByLabelText('graph.param_mode(h)').querySelector('option[value="bound"]')
    expect(option.disabled).toBe(true)
  })
})

describe('GraphEditor save and export', () => {
  it('saves on request, and only when there is something to save', () => {
    const onSave = vi.fn()
    const { rerender } = render(<Harness onSave={onSave} saveStatus="clean" />)
    expect(screen.getByRole('button', { name: /graph.save$/ })).toBeDisabled()
    rerender(<Harness onSave={onSave} saveStatus="dirty" />)
    fireEvent.click(screen.getByRole('button', { name: /graph.save$/ }))
    expect(onSave).toHaveBeenCalled()
    expect(screen.getByTestId('graph-save-status')).toHaveTextContent('graph.status_dirty')
  })

  it('shows the save error the server gave', () => {
    render(<Harness saveStatus="error" saveError="parameter binds unknown node" />)
    expect(screen.getByTestId('graph-save-status')).toHaveTextContent('parameter binds unknown node')
  })

  it('offers a fork instead of a save on a commons cartridge', () => {
    const onForkRequest = vi.fn()
    render(<Harness saveBlockedReason="graph.save_blocked_commons" onForkRequest={onForkRequest} />)
    expect(screen.queryByRole('button', { name: /graph.save$/ })).not.toBeInTheDocument()
    expect(screen.getByTestId('graph-save-status')).toHaveTextContent('graph.save_blocked_commons')
    fireEvent.click(screen.getByRole('button', { name: /graph.fork_to_save/ }))
    expect(onForkRequest).toHaveBeenCalled()
  })

  it('exports the document as a .graph.json download', async () => {
    const createObjectURL = vi.fn(() => 'blob:graph')
    const revokeObjectURL = vi.fn()
    Object.assign(URL, { createObjectURL, revokeObjectURL })
    const clicks = []
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
      clicks.push({ download: this.download, href: this.href })
    })
    render(<Harness />)
    fireEvent.click(screen.getByRole('button', { name: /graph.export/ }))
    expect(clicks).toEqual([{ download: 'flange.graph.json', href: 'blob:graph' }])
    const blob = createObjectURL.mock.calls[0][0]
    const text = await new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.readAsText(blob)
    })
    expect(JSON.parse(text)).toEqual(FLANGE)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:graph')
    clickSpy.mockRestore()
  })

  it('opens the declarations panel', () => {
    render(<Harness />)
    fireEvent.click(screen.getByRole('button', { name: /graph.declarations/ }))
    expect(screen.getByTestId('graph-declarations')).toBeInTheDocument()
  })
})
