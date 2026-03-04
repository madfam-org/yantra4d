import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useUnitSystem } from './useUnitSystem'

beforeEach(() => {
  localStorage.clear()
})

describe('useUnitSystem', () => {
  it('defaults to mm', () => {
    const { result } = renderHook(() => useUnitSystem())
    expect(result.current.unit).toBe('mm')
    expect(result.current.label).toBe('mm')
  })

  it('converts mm values correctly (identity)', () => {
    const { result } = renderHook(() => useUnitSystem())
    expect(result.current.convert(25.4)).toBe(25.4)
  })

  it('formats mm values with suffix', () => {
    const { result } = renderHook(() => useUnitSystem())
    expect(result.current.format(25.4)).toBe('25.4mm')
  })

  it('formats mm values with custom precision', () => {
    const { result } = renderHook(() => useUnitSystem())
    expect(result.current.format(25.456, 2)).toBe('25.46mm')
  })

  it('toggles to inches', () => {
    const { result } = renderHook(() => useUnitSystem())
    act(() => result.current.toggle())
    expect(result.current.unit).toBe('in')
    expect(result.current.label).toBe('in')
  })

  it('converts correctly in inches mode', () => {
    const { result } = renderHook(() => useUnitSystem())
    act(() => result.current.toggle())
    expect(result.current.convert(25.4)).toBeCloseTo(1.0)
  })

  it('formats correctly in inches mode', () => {
    const { result } = renderHook(() => useUnitSystem())
    act(() => result.current.toggle())
    expect(result.current.format(25.4)).toBe('1.0"')
  })

  it('toggles back to mm', () => {
    const { result } = renderHook(() => useUnitSystem())
    act(() => result.current.toggle())
    expect(result.current.unit).toBe('in')
    act(() => result.current.toggle())
    expect(result.current.unit).toBe('mm')
  })

  it('persists to localStorage', () => {
    const { result } = renderHook(() => useUnitSystem())
    act(() => result.current.toggle())
    expect(localStorage.getItem('yantra4d-unit')).toBe('in')
  })

  it('reads persisted unit from localStorage', () => {
    localStorage.setItem('yantra4d-unit', 'in')
    const { result } = renderHook(() => useUnitSystem())
    expect(result.current.unit).toBe('in')
    expect(result.current.label).toBe('in')
  })

  it('setUnit changes unit directly', () => {
    const { result } = renderHook(() => useUnitSystem())
    act(() => result.current.setUnit('in'))
    expect(result.current.unit).toBe('in')
    expect(localStorage.getItem('yantra4d-unit')).toBe('in')
  })

  describe('convertVolume', () => {
    it('returns identity in mm mode', () => {
      const { result } = renderHook(() => useUnitSystem())
      expect(result.current.convertVolume(16387.064)).toBe(16387.064)
    })

    it('converts mm³ to in³ (16387.064 mm³ = 1 in³)', () => {
      const { result } = renderHook(() => useUnitSystem())
      act(() => result.current.toggle())
      expect(result.current.convertVolume(16387.064)).toBeCloseTo(1.0)
    })

    it('converts zero correctly', () => {
      const { result } = renderHook(() => useUnitSystem())
      act(() => result.current.toggle())
      expect(result.current.convertVolume(0)).toBe(0)
    })
  })

  describe('formatVolume', () => {
    it('formats with mm³ suffix in mm mode', () => {
      const { result } = renderHook(() => useUnitSystem())
      expect(result.current.formatVolume(1234)).toBe('1234 mm³')
    })

    it('formats with in³ suffix in inches mode', () => {
      const { result } = renderHook(() => useUnitSystem())
      act(() => result.current.toggle())
      expect(result.current.formatVolume(16387.064)).toBe('1 in³')
    })

    it('respects custom precision', () => {
      const { result } = renderHook(() => useUnitSystem())
      expect(result.current.formatVolume(1234.567, 2)).toBe('1234.57 mm³')
    })

    it('uses precision 0 by default', () => {
      const { result } = renderHook(() => useUnitSystem())
      expect(result.current.formatVolume(1234.567)).toBe('1235 mm³')
    })
  })
})
