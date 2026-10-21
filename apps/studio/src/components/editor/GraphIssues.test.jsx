import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import GraphIssues from './GraphIssues'

const validDoc = {
  version: '1.0.0',
  nodes: [
    { id: 'base', type: 'box', params: { w: 40, d: 20, h: 8 } },
    { id: 'bore', type: 'cylinder', params: { r: 3, h: 40 } },
    { id: 'body', type: 'cut', inputs: { a: 'base', b: 'bore' } },
  ],
  outputs: { part: 'body' },
}

const json = (doc) => JSON.stringify(doc, null, 2)

describe('GraphIssues', () => {
  it('renders nothing for an empty buffer', () => {
    const { container } = render(<GraphIssues content="   " />)
    expect(container).toBeEmptyDOMElement()
  })

  it('reports unparseable JSON without crashing', () => {
    render(<GraphIssues content="{nope" />)
    expect(screen.getByText('Not valid JSON')).toBeInTheDocument()
  })

  it('summarises a valid graph with its evaluation order', () => {
    render(<GraphIssues content={json(validDoc)} />)
    expect(screen.getByText(/Valid · 3 nodes · 1 part/)).toBeInTheDocument()
    const order = screen.getByText(/base/).textContent
    expect(order.indexOf('base')).toBeLessThan(order.indexOf('body'))
    expect(order.indexOf('bore')).toBeLessThan(order.indexOf('body'))
  })

  it('uses singular wording for one node and one part', () => {
    const doc = { version: '1.0.0', nodes: [{ id: 'b', type: 'box' }], outputs: { p: 'b' } }
    render(<GraphIssues content={json(doc)} />)
    expect(screen.getByText(/Valid · 1 node · 1 part/)).toBeInTheDocument()
  })

  it('lists validation problems and says the save will fail', () => {
    const doc = structuredClone(validDoc)
    doc.nodes[2].inputs.b = 'ghost'
    render(<GraphIssues content={json(doc)} />)
    expect(screen.getByText(/1 problem — this will not save/)).toBeInTheDocument()
    expect(screen.getByText(/unknown node "ghost"/)).toBeInTheDocument()
  })

  it('pluralises multiple problems', () => {
    const doc = structuredClone(validDoc)
    doc.version = '9.9'
    doc.nodes[2].inputs.b = 'ghost'
    render(<GraphIssues content={json(doc)} />)
    expect(screen.getByText(/2 problems — this will not save/)).toBeInTheDocument()
  })

  it('attributes a problem to its node and the param it is about', () => {
    const doc = structuredClone(validDoc)
    doc.nodes[0].params.nope = 1
    render(<GraphIssues content={json(doc)} />)
    expect(screen.getByText('base.nope:')).toBeInTheDocument()
  })

  it('attributes a missing input to its socket', () => {
    const doc = structuredClone(validDoc)
    const consumer = doc.nodes.find((n) => n.inputs)
    const socket = Object.keys(consumer.inputs)[0]
    delete consumer.inputs[socket]
    render(<GraphIssues content={json(doc)} />)
    expect(screen.getByText(`${consumer.id}.${socket}:`)).toBeInTheDocument()
  })

  it('selects the node an issue is about when the graph editor is showing', () => {
    const doc = structuredClone(validDoc)
    doc.nodes[0].params.nope = 1
    const onSelectNode = vi.fn()
    render(<GraphIssues content={json(doc)} onSelectNode={onSelectNode} />)
    fireEvent.click(screen.getByRole('button', { name: 'base.nope:' }))
    expect(onSelectNode).toHaveBeenCalledWith('base')
  })

  it('marks profiles in the order and explains the marker', () => {
    const doc = {
      version: '1.0.0',
      nodes: [
        { id: 'outline', type: 'profile_rect', params: { w: 10, d: 10 } },
        { id: 'solid', type: 'extrude', inputs: { profile: 'outline' }, params: { height: 4 } },
      ],
      outputs: { part: 'solid' },
    }
    render(<GraphIssues content={json(doc)} />)
    expect(screen.getByText(/outline\*/)).toBeInTheDocument()
    expect(screen.getByText(/consumed by extrude/)).toBeInTheDocument()
  })

  it('does not mark a profile when there is none', () => {
    render(<GraphIssues content={json(validDoc)} />)
    expect(screen.queryByText(/consumed by extrude/)).not.toBeInTheDocument()
  })
})
