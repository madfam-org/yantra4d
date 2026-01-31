import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useLocalStoragePersistence } from './useLocalStoragePersistence'

beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useLocalStoragePersistence', () => {
  it('writes JSON-serialized value to localStorage after debounce', () => {
    renderHook(() => useLocalStoragePersistence('test-key', { a: 1 }))
    expect(localStorage.getItem('test-key')).toBeNull()
    vi.advanceTimersByTime(300)
    expect(localStorage.getItem('test-key')).toBe('{"a":1}')
  })

  it('writes immediately when debounce is 0', () => {
    renderHook(() => useLocalStoragePersistence('imm-key', 'val', { debounce: 0, serialize: false }))
    expect(localStorage.getItem('imm-key')).toBe('val')
  })

  it('stores raw string when serialize=false', () => {
    renderHook(() => useLocalStoragePersistence('raw-key', 'raw-val', { debounce: 0, serialize: false }))
    expect(localStorage.getItem('raw-key')).toBe('raw-val')
  })

  it('cleans up timer on key change', () => {
    const { rerender } = renderHook(
      ({ key }) => useLocalStoragePersistence(key, 'v'),
      { initialProps: { key: 'key1' } }
    )
    rerender({ key: 'key2' })
    vi.advanceTimersByTime(300)
    // key1 should not have been written (timer was cleared)
    expect(localStorage.getItem('key1')).toBeNull()
    expect(localStorage.getItem('key2')).toBe('"v"')
  })
})
