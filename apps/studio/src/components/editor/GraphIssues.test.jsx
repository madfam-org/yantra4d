import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
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

  it('attributes a problem to its node', () => {
    const doc = structuredClone(validDoc)
    doc.nodes[0].params.nope = 1
    render(<GraphIssues content={json(doc)} />)
    expect(screen.getByText('base:')).toBeInTheDocument()
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

  describe('expression inputs', () => {
    const exprDoc = (expr) => {
      const doc = structuredClone(validDoc)
      doc.version = '1.1.0'
      doc.nodes[0].params.w = { expr }
      return doc
    }
    const manifest = { parameters: [{ id: 'plate_width' }, { id: 'other' }] }

    it('accepts an expression over a declared parameter', () => {
      render(<GraphIssues content={json(exprDoc('plate_width / 2'))} manifest={manifest} />)
      expect(screen.queryByText(/will not save/)).not.toBeInTheDocument()
    })

    it('reports an identifier no manifest parameter declares', () => {
      render(<GraphIssues content={json(exprDoc('mystery * 2'))} manifest={manifest} />)
      expect(screen.getByText(/undeclared manifest parameter/)).toBeInTheDocument()
    })

    it('reports a syntax error while the author types', () => {
      render(<GraphIssues content={json(exprDoc('(1 + 2'))} manifest={manifest} />)
      expect(screen.getByText(/is not valid/)).toBeInTheDocument()
    })

    it('only syntax-checks identifiers when no manifest is supplied', () => {
      render(<GraphIssues content={json(exprDoc('mystery * 2'))} />)
      expect(screen.queryByText(/undeclared manifest parameter/)).not.toBeInTheDocument()
    })

    it('tolerates a manifest with no parameters array', () => {
      render(<GraphIssues content={json(exprDoc('mystery * 2'))} manifest={{}} />)
      expect(screen.queryByText(/will not save/)).not.toBeInTheDocument()
    })
  })
})
