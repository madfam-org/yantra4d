import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePanelLayout } from './usePanelLayout'

const STORAGE_KEY = 'yantra4d-panel-layout'

beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('usePanelLayout', () => {
  it('returns default layout when localStorage is empty', () => {
    const { result } = renderHook(() => usePanelLayout())
    expect(result.current.layout).toEqual({
      sidebarSize: 25,
      sidebarCollapsed: false,
      consoleSize: 30,
      consoleCollapsed: false,
    })
  })

  it('reads persisted layout from localStorage', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      sidebarSize: 30,
      sidebarCollapsed: true,
      consoleSize: 20,
      consoleCollapsed: false,
    }))
    const { result } = renderHook(() => usePanelLayout())
    expect(result.current.layout.sidebarSize).toBe(30)
    expect(result.current.layout.sidebarCollapsed).toBe(true)
    expect(result.current.layout.consoleSize).toBe(20)
  })

  it('falls back to defaults on corrupted localStorage', () => {
    localStorage.setItem(STORAGE_KEY, 'not-json')
    const { result } = renderHook(() => usePanelLayout())
    expect(result.current.layout.sidebarSize).toBe(25)
  })

  it('setSidebarSize updates sidebar size', () => {
    const { result } = renderHook(() => usePanelLayout())
    act(() => result.current.setSidebarSize(35))
    expect(result.current.layout.sidebarSize).toBe(35)
  })

  it('toggleSidebar toggles sidebarCollapsed', () => {
    const { result } = renderHook(() => usePanelLayout())
    expect(result.current.layout.sidebarCollapsed).toBe(false)
    act(() => result.current.toggleSidebar())
    expect(result.current.layout.sidebarCollapsed).toBe(true)
    act(() => result.current.toggleSidebar())
    expect(result.current.layout.sidebarCollapsed).toBe(false)
  })

  it('setConsoleSize updates console size', () => {
    const { result } = renderHook(() => usePanelLayout())
    act(() => result.current.setConsoleSize(40))
    expect(result.current.layout.consoleSize).toBe(40)
  })

  it('toggleConsole toggles consoleCollapsed', () => {
    const { result } = renderHook(() => usePanelLayout())
    act(() => result.current.toggleConsole())
    expect(result.current.layout.consoleCollapsed).toBe(true)
  })

  it('persists layout to localStorage after debounce', () => {
    const { result } = renderHook(() => usePanelLayout())
    act(() => result.current.setSidebarSize(40))
    // Not persisted yet (debounce)
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
    // Advance past debounce
    act(() => vi.advanceTimersByTime(350))
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY))
    expect(stored.sidebarSize).toBe(40)
  })

  it('merges partial localStorage with defaults', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ sidebarSize: 18 }))
    const { result } = renderHook(() => usePanelLayout())
    expect(result.current.layout.sidebarSize).toBe(18)
    expect(result.current.layout.consoleSize).toBe(30) // default
    expect(result.current.layout.sidebarCollapsed).toBe(false) // default
  })
})
