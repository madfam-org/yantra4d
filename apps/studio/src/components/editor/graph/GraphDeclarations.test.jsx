import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

vi.mock('../../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({
    t: (key, params) => (params ? `${key}(${Object.values(params).join(',')})` : key),
  }),
}))

import GraphDeclarations from './GraphDeclarations'
import { buildScope } from '../../../lib/graph/graphExpressions'

const MANIFEST = [
  { id: 'b_od', type: 'slider', default: 22 },
  { id: 'nema', type: 'select', default: 'NEMA17', options: [{ value: 'NEMA17' }, { value: 'NEMA23' }] },
]

function doc(extra = {}) {
  return {
    version: '1.1.0',
    nodes: [{ id: 'body', type: 'box' }],
    outputs: { part: 'body' },
    parameters: { b_od: { default: 22 }, nema: { default: 'NEMA17' }, gone: { default: 3 } },
    derived: [{ id: 'seat_r', expr: 'b_od / 2' }, { id: 'wall', expr: 'seat_r + 2' }],
    ...extra,
  }
}

function setup(d = doc()) {
  const onDocChange = vi.fn()
  const { scope, issues } = buildScope(d)
  render(<GraphDeclarations doc={d} manifestParameters={MANIFEST} scope={scope} issues={issues} onDocChange={onDocChange} />)
  return { onDocChange, last: () => onDocChange.mock.calls[onDocChange.mock.calls.length - 1][0] }
}

describe('GraphDeclarations: declared parameters', () => {
  it('lists each declared parameter with the value expressions see', () => {
    setup()
    expect(screen.getByTestId('graph-declared-b_od')).toHaveTextContent('= 22')
    expect(screen.getByTestId('graph-declared-nema')).toHaveTextContent('= —')
  })

  it('warns when a declared id is not in the manifest', () => {
    setup()
    expect(screen.getByText('graph.declared_missing_from_manifest(gone)')).toBeInTheDocument()
    expect(screen.queryByText('graph.declared_missing_from_manifest(b_od)')).not.toBeInTheDocument()
  })

  it('requires a map for a named select and takes the numbers from the author', () => {
    const { onDocChange, last } = setup()
    expect(screen.getByText('graph.map_required(nema)')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('graph.map_value(nema,NEMA17)'), { target: { value: '17' } })
    expect(last().parameters.nema).toEqual({ default: 'NEMA17', map: { NEMA17: 17 } })
    expect(onDocChange).toHaveBeenCalledTimes(1)
  })

  it('clears a map entry that is emptied', () => {
    const d = doc({ parameters: { nema: { default: 'NEMA17', map: { NEMA17: 17 } } } })
    const { last } = setup(d)
    expect(screen.queryByText('graph.map_required(nema)')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('graph.map_value(nema,NEMA17)'), { target: { value: '' } })
    expect(last().parameters.nema).toEqual({ default: 'NEMA17' })
  })

  it('removes a declaration', () => {
    const { last } = setup()
    fireEvent.click(screen.getByLabelText('graph.undeclare(gone)'))
    expect(Object.keys(last().parameters)).toEqual(['b_od', 'nema'])
  })

  it('says so when nothing is declared', () => {
    setup({ version: '1.0.0', nodes: [], outputs: {} })
    expect(screen.getByText('graph.no_declared_parameters')).toBeInTheDocument()
  })
})

describe('GraphDeclarations: derived values', () => {
  it('shows each value in order', () => {
    setup()
    expect(screen.getByTestId('graph-derived-seat_r')).toHaveTextContent('= 11')
    expect(screen.getByTestId('graph-derived-wall')).toHaveTextContent('= 13')
  })

  it('flags a value that reads a later one', () => {
    setup(doc({ derived: [{ id: 'wall', expr: 'seat_r + 2' }, { id: 'seat_r', expr: 'b_od / 2' }] }))
    expect(screen.getByTestId('graph-derived-wall')).toHaveTextContent(/seat_r/)
  })

  it('edits, reorders and removes', () => {
    const { last } = setup()
    fireEvent.change(screen.getByLabelText('graph.derived_expr(wall)'), { target: { value: 'seat_r + 3' } })
    expect(last().derived[1]).toEqual({ id: 'wall', expr: 'seat_r + 3' })
    expect(screen.getByLabelText('graph.move_up(seat_r)')).toBeDisabled()
    expect(screen.getByLabelText('graph.move_down(wall)')).toBeDisabled()
    fireEvent.click(screen.getByLabelText('graph.move_down(seat_r)'))
    expect(last().derived.map((d) => d.id)).toEqual(['wall', 'seat_r'])
    fireEvent.click(screen.getByLabelText('graph.move_up(wall)'))
    expect(last().derived.map((d) => d.id)).toEqual(['wall', 'seat_r'])
    fireEvent.click(screen.getByLabelText('graph.remove_derived(seat_r)'))
    expect(last().derived.map((d) => d.id)).toEqual(['wall'])
  })

  it('adds a value, and explains a refused id', () => {
    const { last, onDocChange } = setup()
    const add = screen.getByText('graph.add_derived')
    expect(add).toBeDisabled()
    fireEvent.change(screen.getByLabelText('graph.derived_new_id'), { target: { value: 'seat_r' } })
    fireEvent.change(screen.getByLabelText('graph.derived_new_expr'), { target: { value: '1' } })
    fireEvent.click(add)
    expect(onDocChange).not.toHaveBeenCalled()
    expect(screen.getByText(/already defined/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('graph.derived_new_id'), { target: { value: 'bolt_r' } })
    fireEvent.keyDown(screen.getByLabelText('graph.derived_new_expr'), { key: 'Enter' })
    expect(last().derived.map((d) => d.id)).toEqual(['seat_r', 'wall', 'bolt_r'])
  })
})
