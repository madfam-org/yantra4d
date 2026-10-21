import { describe, it, expect } from 'vitest'
import { parameterModes, isParameterInMode } from './parameterModes'

describe('parameterModes', () => {
  it('reads `modes` when `visible_in_modes` is absent', () => {
    expect(parameterModes({ modes: ['bin'] })).toEqual(['bin'])
    expect(isParameterInMode({ modes: ['bin'] }, 'cup')).toBe(false)
    expect(isParameterInMode({ modes: ['bin', 'baseplate'] }, 'baseplate')).toBe(true)
  })

  it('prefers `visible_in_modes` when both are present', () => {
    const param = { visible_in_modes: ['cup'], modes: ['bin'] }
    expect(parameterModes(param)).toEqual(['cup'])
    expect(isParameterInMode(param, 'cup')).toBe(true)
    expect(isParameterInMode(param, 'bin')).toBe(false)
  })

  it('treats an unscoped parameter as visible in every mode', () => {
    expect(parameterModes({})).toBeUndefined()
    expect(isParameterInMode({}, 'anything')).toBe(true)
  })

  it('keeps an empty list as scoped to no mode', () => {
    expect(isParameterInMode({ visible_in_modes: [] }, 'assembly')).toBe(false)
    expect(isParameterInMode({ modes: [] }, 'assembly')).toBe(false)
  })

  it('ignores a non-array scope', () => {
    expect(isParameterInMode({ modes: 'bin' }, 'cup')).toBe(true)
  })
})
