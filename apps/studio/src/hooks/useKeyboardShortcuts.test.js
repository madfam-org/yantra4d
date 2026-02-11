import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useKeyboardShortcuts } from './useKeyboardShortcuts'

function fireKey(key, opts = {}) {
  const event = new KeyboardEvent('keydown', {
    key,
    bubbles: true,
    ...opts,
  })
  // Allow preventDefault tracking
  const spy = vi.spyOn(event, 'preventDefault')
  window.dispatchEvent(event)
  return spy
}

function renderShortcuts(overrides = {}) {
  const defaults = {
    onUndo: vi.fn(),
    onRedo: vi.fn(),
    onRender: vi.fn(),
    onCancelRender: vi.fn(),
    onSwitchMode: vi.fn(),
    loading: false,
    modes: [{ id: 'basic' }, { id: 'advanced' }, { id: 'remix' }],
  }
  const opts = { ...defaults, ...overrides }
  return { ...renderHook(() => useKeyboardShortcuts(opts)), opts }
}

describe('useKeyboardShortcuts', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ---------- Undo: Cmd/Ctrl+Z ----------
  it('fires onUndo on Ctrl+Z', () => {
    const { opts } = renderShortcuts()
    fireKey('z', { ctrlKey: true })
    expect(opts.onUndo).toHaveBeenCalledTimes(1)
  })

  it('fires onUndo on Meta+Z (Mac)', () => {
    const { opts } = renderShortcuts()
    fireKey('z', { metaKey: true })
    expect(opts.onUndo).toHaveBeenCalledTimes(1)
  })

  it('prevents default on Ctrl+Z', () => {
    renderShortcuts()
    const spy = fireKey('z', { ctrlKey: true })
    expect(spy).toHaveBeenCalled()
  })

  // ---------- Redo: Cmd/Ctrl+Shift+Z ----------
  it('fires onRedo on Ctrl+Shift+Z', () => {
    const { opts } = renderShortcuts()
    fireKey('z', { ctrlKey: true, shiftKey: true })
    expect(opts.onRedo).toHaveBeenCalledTimes(1)
    expect(opts.onUndo).not.toHaveBeenCalled() // not confused with undo
  })

  it('fires onRedo on Meta+Shift+Z (Mac)', () => {
    const { opts } = renderShortcuts()
    fireKey('z', { metaKey: true, shiftKey: true })
    expect(opts.onRedo).toHaveBeenCalledTimes(1)
  })

  // ---------- Render: Cmd/Ctrl+Enter ----------
  it('fires onRender on Ctrl+Enter', () => {
    const { opts } = renderShortcuts()
    fireKey('Enter', { ctrlKey: true })
    expect(opts.onRender).toHaveBeenCalledTimes(1)
  })

  it('fires onRender on Meta+Enter', () => {
    const { opts } = renderShortcuts()
    fireKey('Enter', { metaKey: true })
    expect(opts.onRender).toHaveBeenCalledTimes(1)
  })

  // ---------- Cancel: Escape while loading ----------
  it('fires onCancelRender on Escape when loading', () => {
    const { opts } = renderShortcuts({ loading: true })
    fireKey('Escape')
    expect(opts.onCancelRender).toHaveBeenCalledTimes(1)
  })

  it('does NOT fire onCancelRender on Escape when not loading', () => {
    const { opts } = renderShortcuts({ loading: false })
    fireKey('Escape')
    expect(opts.onCancelRender).not.toHaveBeenCalled()
  })

  // ---------- Mode switch: Cmd/Ctrl+1..N ----------
  it('switches to mode 1 on Ctrl+1', () => {
    const { opts } = renderShortcuts()
    fireKey('1', { ctrlKey: true })
    expect(opts.onSwitchMode).toHaveBeenCalledWith('basic')
  })

  it('switches to mode 2 on Ctrl+2', () => {
    const { opts } = renderShortcuts()
    fireKey('2', { ctrlKey: true })
    expect(opts.onSwitchMode).toHaveBeenCalledWith('advanced')
  })

  it('switches to mode 3 on Meta+3', () => {
    const { opts } = renderShortcuts()
    fireKey('3', { metaKey: true })
    expect(opts.onSwitchMode).toHaveBeenCalledWith('remix')
  })

  it('ignores Ctrl+N when N > modes.length', () => {
    const { opts } = renderShortcuts()
    fireKey('9', { ctrlKey: true })
    expect(opts.onSwitchMode).not.toHaveBeenCalled()
  })

  it('ignores Ctrl+0', () => {
    const { opts } = renderShortcuts()
    fireKey('0', { ctrlKey: true })
    expect(opts.onSwitchMode).not.toHaveBeenCalled()
  })

  // ---------- Edge cases ----------
  it('does nothing for unmodified letter keys', () => {
    const { opts } = renderShortcuts()
    fireKey('a')
    expect(opts.onUndo).not.toHaveBeenCalled()
    expect(opts.onRedo).not.toHaveBeenCalled()
    expect(opts.onRender).not.toHaveBeenCalled()
  })

  it('handles null callbacks gracefully', () => {
    renderShortcuts({
      onUndo: undefined,
      onRedo: undefined,
      onRender: undefined,
      onCancelRender: undefined,
      onSwitchMode: undefined,
    })
    // should not throw
    fireKey('z', { ctrlKey: true })
    fireKey('z', { ctrlKey: true, shiftKey: true })
    fireKey('Enter', { ctrlKey: true })
    fireKey('Escape')
  })

  it('cleans up event listener on unmount', () => {
    const removeSpy = vi.spyOn(window, 'removeEventListener')
    const { unmount } = renderShortcuts()
    unmount()
    expect(removeSpy).toHaveBeenCalledWith('keydown', expect.any(Function), { capture: true })
  })

  it('handles empty modes array', () => {
    const { opts } = renderShortcuts({ modes: [] })
    fireKey('1', { ctrlKey: true })
    expect(opts.onSwitchMode).not.toHaveBeenCalled()
  })

  it('handles undefined modes', () => {
    renderShortcuts({ modes: undefined })
    // should not throw
    fireKey('1', { ctrlKey: true })
  })
})
