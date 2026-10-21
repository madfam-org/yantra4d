import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

vi.mock('../../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({
    t: (key, params) => (params ? `${key}(${Object.values(params).join(',')})` : key),
  }),
}))

import GraphParamField from './GraphParamField'
import { evaluateSafeFormula } from '../../../lib/safeFormula'

const FLOAT = { kind: 'float', default: 10, bindable: true, expr: true }
const COUNT = { kind: 'count', default: 3, bindable: true }
const PLANE = { kind: 'plane', default: 'XY', bindable: false }
const SELECTOR = { kind: 'selector', default: '', bindable: false }

/** An expression checker over {width: 40, wall: 2}; anything else is undeclared. */
function checkExpression(expr) {
  const ids = (expr.match(/[A-Za-z_]\w*/g) ?? [])
  const undeclared = ids.filter((id) => !['width', 'wall'].includes(id))
  if (undeclared.length) return { error: `reads ${undeclared.join(', ')}`, undeclared }
  if (expr.includes('>')) return { value: true, undeclared: [] }
  if (expr.trim() === '' || expr.endsWith('+')) return { error: 'Expected value', undeclared: [] }
  return { value: evaluateSafeFormula(expr, { width: 40, wall: 2 }), undeclared: [] }
}

function setup(props = {}) {
  const handlers = {
    onLiteral: vi.fn(), onReset: vi.fn(), onBind: vi.fn(), onExpression: vi.fn(), onDeclare: vi.fn(),
  }
  const all = {
    nodeId: 'body', name: 'w', spec: FLOAT, value: undefined, boundTo: null,
    bindable: [{ id: 'width' }, { id: 'depth' }], bindBlockedReason: null,
    checkExpression, manifestIds: ['width', 'wall', 'height'], ...handlers, ...props,
  }
  const utils = render(<GraphParamField {...all} />)
  return { ...handlers, ...utils, props: all }
}

describe('GraphParamField literals', () => {
  it('shows the catalog default when nothing is stored, and no reset', () => {
    setup()
    expect(screen.getByLabelText('graph.param_value(w)')).toHaveValue(10)
    expect(screen.queryByText('graph.reset_default')).not.toBeInTheDocument()
  })

  it('commits a number once it parses, not while it is half typed', () => {
    const { onLiteral } = setup({ value: 5 })
    const input = screen.getByLabelText('graph.param_value(w)')
    fireEvent.change(input, { target: { value: '' } })
    expect(onLiteral).not.toHaveBeenCalled()
    fireEvent.change(input, { target: { value: '7.5' } })
    expect(onLiteral).toHaveBeenCalledWith(7.5)
  })

  it('truncates a count to a whole number', () => {
    const { onLiteral } = setup({ name: 'count', spec: COUNT, value: 3 })
    fireEvent.change(screen.getByLabelText('graph.param_value(count)'), { target: { value: '4.8' } })
    expect(onLiteral).toHaveBeenCalledWith(4)
  })

  it('picks a plane from the catalog list', () => {
    const { onLiteral } = setup({ name: 'plane', spec: PLANE, value: 'XY' })
    fireEvent.change(screen.getByLabelText('graph.param_value(plane)'), { target: { value: 'XZ' } })
    expect(onLiteral).toHaveBeenCalledWith('XZ')
    // structural params offer no mode switch at all
    expect(screen.queryByLabelText('graph.param_mode(plane)')).not.toBeInTheDocument()
  })

  it('picks an axis', () => {
    const { onLiteral } = setup({ name: 'axis', spec: { kind: 'axis', default: 'z', bindable: false }, value: 'z' })
    fireEvent.change(screen.getByLabelText('graph.param_value(axis)'), { target: { value: 'x' } })
    expect(onLiteral).toHaveBeenCalledWith('x')
  })

  it('edits a selector as text', () => {
    const { onLiteral } = setup({ name: 'edges', spec: SELECTOR, value: '' })
    fireEvent.change(screen.getByLabelText('graph.param_value(edges)'), { target: { value: '|Z' } })
    expect(onLiteral).toHaveBeenCalledWith('|Z')
  })

  it('edits a kind it does not know as JSON, committed only when it parses', () => {
    const spec = { kind: 'curve', default: [[0, 0]], bindable: false }
    const { onLiteral } = setup({ name: 'curve', spec, value: [[0, 0], [1, 0]] })
    const box = screen.getByLabelText('graph.param_value(curve)')
    fireEvent.change(box, { target: { value: '[[0,' } })
    expect(onLiteral).not.toHaveBeenCalled()
    expect(screen.getByText('graph.json_invalid')).toBeInTheDocument()
    fireEvent.change(box, { target: { value: '[[0, 0], [2, 0]]' } })
    expect(onLiteral).toHaveBeenCalledWith([[0, 0], [2, 0]])
    expect(screen.queryByText('graph.json_invalid')).not.toBeInTheDocument()
  })

  it('resets a stored value', () => {
    const { onReset } = setup({ value: 5 })
    fireEvent.click(screen.getByText('graph.reset_default'))
    expect(onReset).toHaveBeenCalled()
  })

  it('flags an invalid literal even before the validator does', () => {
    setup({ name: 'count', spec: COUNT, value: 0 })
    expect(screen.getByText(/between 1 and/)).toBeInTheDocument()
  })

  it('shows the validator issue on its row', () => {
    setup({ issue: { message: '"w" needs a finite number.', nodeId: 'body', param: 'w' } })
    expect(screen.getByRole('alert')).toHaveTextContent('needs a finite number')
  })

  it('re-syncs when the stored value changes from outside', () => {
    const { rerender, props } = setup({ value: 5 })
    rerender(<GraphParamField {...props} value={9} />)
    expect(screen.getByLabelText('graph.param_value(w)')).toHaveValue(9)
  })
})

describe('GraphParamField modes', () => {
  it('offers expression mode only when the catalog allows it', () => {
    setup({ spec: { ...FLOAT, expr: false } })
    const modes = [...screen.getByLabelText('graph.param_mode(w)').options].map((o) => o.value)
    expect(modes).toEqual(['literal', 'bound'])
  })

  it('turns a literal into an expression that starts from it', () => {
    const { onExpression } = setup({ value: 12 })
    fireEvent.change(screen.getByLabelText('graph.param_mode(w)'), { target: { value: 'expr' } })
    expect(onExpression).toHaveBeenCalledWith('12')
  })

  it('turns an expression back into the literal it evaluates to', () => {
    const { onLiteral } = setup({ value: { expr: 'width / 2 - wall' } })
    fireEvent.change(screen.getByLabelText('graph.param_mode(w)'), { target: { value: 'literal' } })
    expect(onLiteral).toHaveBeenCalledWith(18)
  })

  it('falls back to the default when the expression does not evaluate', () => {
    const { onReset, onLiteral } = setup({ value: { expr: 'height * 2' } })
    fireEvent.change(screen.getByLabelText('graph.param_mode(w)'), { target: { value: 'literal' } })
    expect(onReset).toHaveBeenCalled()
    expect(onLiteral).not.toHaveBeenCalled()
  })

  it('binds to the first bindable manifest parameter, and unbinds when leaving', () => {
    const { onBind, unmount } = setup({ value: 12 })
    fireEvent.change(screen.getByLabelText('graph.param_mode(w)'), { target: { value: 'bound' } })
    expect(onBind).toHaveBeenCalledWith('width')
    unmount()
    const second = setup({ value: 12, boundTo: 'width' })
    expect(screen.getByText('graph.bound_default(12)')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('graph.param_binding(w)'), { target: { value: 'depth' } })
    expect(second.onBind).toHaveBeenCalledWith('depth')
    fireEvent.change(screen.getByLabelText('graph.param_mode(w)'), { target: { value: 'literal' } })
    expect(second.onBind).toHaveBeenCalledWith(null)
  })

  it('binding replaces an expression with the default first', () => {
    const { onReset, onBind } = setup({ value: { expr: 'width' } })
    fireEvent.change(screen.getByLabelText('graph.param_mode(w)'), { target: { value: 'bound' } })
    expect(onReset).toHaveBeenCalled()
    expect(onBind).toHaveBeenCalledWith('width')
  })

  it('cannot bind while binding is blocked', () => {
    setup({ bindBlockedReason: 'not a fork' })
    const option = screen.getByLabelText('graph.param_mode(w)').querySelector('option[value="bound"]')
    expect(option.disabled).toBe(true)
  })

  it('selecting the current mode does nothing', () => {
    const { onLiteral, onReset, onBind, onExpression } = setup({ value: 3 })
    fireEvent.change(screen.getByLabelText('graph.param_mode(w)'), { target: { value: 'literal' } })
    for (const fn of [onLiteral, onReset, onBind, onExpression]) expect(fn).not.toHaveBeenCalled()
  })
})

describe('GraphParamField expressions', () => {
  it('shows what the expression evaluates to', () => {
    setup({ value: { expr: 'width / 2' } })
    expect(screen.getByText('= 20')).toBeInTheDocument()
  })

  it('sends every keystroke so the validator runs live', () => {
    const { onExpression } = setup({ value: { expr: 'width' } })
    fireEvent.change(screen.getByTestId('graph-expr-body-w'), { target: { value: 'width +' } })
    expect(onExpression).toHaveBeenCalledWith('width +')
    expect(screen.getByText('Expected value')).toBeInTheDocument()
  })

  it('offers to declare a manifest parameter the expression reads', () => {
    const { onDeclare } = setup({ value: { expr: 'height / 2' } })
    fireEvent.click(screen.getByText('graph.declare_parameter(height)'))
    expect(onDeclare).toHaveBeenCalledWith('height')
  })

  it('says when an identifier is not a manifest parameter at all', () => {
    setup({ value: { expr: 'ghost / 2' } })
    expect(screen.getByText('graph.not_a_manifest_parameter(ghost)')).toBeInTheDocument()
    expect(screen.queryByText(/graph.declare_parameter/)).not.toBeInTheDocument()
  })
})

describe('GraphParamField Wave D kinds', () => {
  const CONDITION = { kind: 'condition', default: true, bindable: false, expr: true }
  const POINTS = { kind: 'points', default: [[0, 0], [10, 0], [0, 10]], bindable: false, expr: true }

  it('a condition is true or false, or an expression', () => {
    const { onLiteral } = setup({ name: 'when', spec: CONDITION, value: true })
    fireEvent.change(screen.getByLabelText('graph.param_value(when)'), { target: { value: 'false' } })
    expect(onLiteral).toHaveBeenCalledWith(false)
    const modes = [...screen.getByLabelText('graph.param_mode(when)').options].map((o) => o.value)
    expect(modes).toEqual(['literal', 'expr'])
  })

  it('a condition expression may give a boolean, and turns back into one', () => {
    const { onLiteral } = setup({ name: 'when', spec: CONDITION, value: { expr: 'width > 10' } })
    expect(screen.getByText('= true')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('graph.param_mode(when)'), { target: { value: 'literal' } })
    expect(onLiteral).toHaveBeenCalledWith(true)
  })

  it('edits points row by row: numbers are literals, anything else an expression', () => {
    const { onLiteral } = setup({ name: 'points', spec: POINTS, value: [[0, 0], [10, 0], [0, 10]] })
    // a points list is never a whole expression, so there is no mode switch
    expect(screen.queryByLabelText('graph.param_mode(points)')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('graph.point_coordinate(2,x)'), { target: { value: '12.5' } })
    expect(onLiteral).toHaveBeenLastCalledWith([[0, 0], [12.5, 0], [0, 10]])
    fireEvent.change(screen.getByLabelText('graph.point_coordinate(3,y)'), { target: { value: 'width / 2' } })
    expect(onLiteral).toHaveBeenLastCalledWith([[0, 0], [10, 0], [0, { expr: 'width / 2' }]])
  })

  it('adds and removes points within 3..the catalog limit', () => {
    const { onLiteral } = setup({ name: 'points', spec: POINTS, value: [[0, 0], [10, 0], [0, 10]] })
    expect(screen.getByLabelText('graph.point_remove(1)')).toBeDisabled()
    fireEvent.click(screen.getByText('graph.point_add'))
    expect(onLiteral).toHaveBeenLastCalledWith([[0, 0], [10, 0], [0, 10], [0, 0]])
  })

  it('removes a point when there are more than three', () => {
    const { onLiteral } = setup({ name: 'points', spec: POINTS, value: [[0, 0], [10, 0], [0, 10], [5, 5]] })
    fireEvent.click(screen.getByLabelText('graph.point_remove(2)'))
    expect(onLiteral).toHaveBeenLastCalledWith([[0, 0], [0, 10], [5, 5]])
  })

  it('without coordinate expressions, a non-number is not committed', () => {
    const { onLiteral } = setup({ name: 'points', spec: { ...POINTS, expr: false }, value: [[0, 0], [10, 0], [0, 10]] })
    fireEvent.change(screen.getByLabelText('graph.point_coordinate(1,x)'), { target: { value: 'width' } })
    expect(onLiteral).not.toHaveBeenCalled()
  })

  it('shows an expression coordinate as its text', () => {
    setup({ name: 'points', spec: POINTS, value: [[0, 0], [{ expr: 'wall' }, 0], [0, 10]] })
    expect(screen.getByLabelText('graph.point_coordinate(2,x)')).toHaveValue('wall')
  })
})
