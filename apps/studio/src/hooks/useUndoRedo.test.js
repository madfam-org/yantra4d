import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useUndoRedo } from './useUndoRedo'

describe('useUndoRedo', () => {
  it('initializes with given value', () => {
    const { result } = renderHook(() => useUndoRedo({ x: 1 }))
    const [value] = result.current
    expect(value).toEqual({ x: 1 })
  })

  it('initializes with lazy initializer function', () => {
    const { result } = renderHook(() => useUndoRedo(() => ({ x: 42 })))
    const [value] = result.current
    expect(value).toEqual({ x: 42 })
  })

  it('starts with canUndo=false and canRedo=false', () => {
    const { result } = renderHook(() => useUndoRedo({ a: 1 }))
    const [, , { canUndo, canRedo }] = result.current
    expect(canUndo).toBe(false)
    expect(canRedo).toBe(false)
  })

  it('tracks changes and enables undo', () => {
    const { result } = renderHook(() => useUndoRedo({ x: 1 }))

    act(() => { result.current[1]({ x: 2 }) })

    const [value, , { canUndo }] = result.current
    expect(value).toEqual({ x: 2 })
    expect(canUndo).toBe(true)
  })

  it('undo restores previous value', () => {
    const { result } = renderHook(() => useUndoRedo({ x: 1 }))

    act(() => { result.current[1]({ x: 2 }) })
    act(() => { result.current[2].undo() })

    expect(result.current[0]).toEqual({ x: 1 })
  })

  it('redo re-applies undone change', () => {
    const { result } = renderHook(() => useUndoRedo({ x: 1 }))

    act(() => { result.current[1]({ x: 2 }) })
    act(() => { result.current[2].undo() })
    act(() => { result.current[2].redo() })

    expect(result.current[0]).toEqual({ x: 2 })
  })

  it('undo on empty history is a no-op', () => {
    const { result } = renderHook(() => useUndoRedo({ x: 1 }))
    act(() => { result.current[2].undo() })
    expect(result.current[0]).toEqual({ x: 1 })
  })

  it('redo with nothing to redo is a no-op', () => {
    const { result } = renderHook(() => useUndoRedo({ x: 1 }))
    act(() => { result.current[2].redo() })
    expect(result.current[0]).toEqual({ x: 1 })
  })

  it('new change after undo truncates redo history', () => {
    const { result } = renderHook(() => useUndoRedo({ x: 1 }))

    // Build history: x:1 -> x:2 -> x:3
    act(() => { result.current[1]({ x: 2 }) })
    act(() => { result.current[1]({ x: 3 }) })

    // Undo to x:2
    act(() => { result.current[2].undo() })
    expect(result.current[0]).toEqual({ x: 2 })

    // New change from x:2 should truncate the x:3 redo entry
    act(() => { result.current[1]({ x: 99 }) })

    expect(result.current[0]).toEqual({ x: 99 })

    // Undo should go back to x:2 (not x:3) — proving truncation worked
    act(() => { result.current[2].undo() })
    expect(result.current[0]).toEqual({ x: 2 })
  })

  it('supports functional updater', () => {
    const { result } = renderHook(() => useUndoRedo({ count: 0 }))

    act(() => {
      result.current[1](prev => ({ count: prev.count + 1 }))
    })

    expect(result.current[0]).toEqual({ count: 1 })
  })

  it('skips duplicate values (no-op if unchanged)', () => {
    const { result } = renderHook(() => useUndoRedo({ x: 1 }))

    act(() => { result.current[1]({ x: 1 }) })

    expect(result.current[2].canUndo).toBe(false)
  })

  it('handles multiple undo steps', () => {
    const { result } = renderHook(() => useUndoRedo({ x: 1 }))

    act(() => { result.current[1]({ x: 2 }) })
    act(() => { result.current[1]({ x: 3 }) })
    act(() => { result.current[1]({ x: 4 }) })

    act(() => { result.current[2].undo() })
    expect(result.current[0]).toEqual({ x: 3 })
    act(() => { result.current[2].undo() })
    expect(result.current[0]).toEqual({ x: 2 })
    act(() => { result.current[2].undo() })
    expect(result.current[0]).toEqual({ x: 1 })
    expect(result.current[2].canUndo).toBe(false)
  })
})
