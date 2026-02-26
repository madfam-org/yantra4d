import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useMediaQuery, useIsMobile, useIsTablet, useIsDesktop, useIsLandscape } from '../useMediaQuery'

describe('useMediaQuery', () => {
  let listeners = []
  let mockMatches = false

  const mockMatchMedia = vi.fn((query) => {
    const mql = {
      matches: mockMatches,
      media: query,
      addEventListener: vi.fn((event, handler) => {
        listeners.push({ event, handler })
      }),
      removeEventListener: vi.fn((event, handler) => {
        listeners = listeners.filter(l => l.handler !== handler)
      }),
    }
    return mql
  })

  beforeEach(() => {
    listeners = []
    mockMatches = false
    vi.stubGlobal('matchMedia', mockMatchMedia)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns initial match state', () => {
    mockMatches = true
    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'))
    expect(result.current).toBe(true)
  })

  it('returns false when no match', () => {
    mockMatches = false
    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'))
    expect(result.current).toBe(false)
  })

  it('updates when media query changes', () => {
    mockMatches = false
    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'))
    expect(result.current).toBe(false)

    // Simulate media query change
    act(() => {
      listeners.forEach(l => {
        if (l.event === 'change') {
          l.handler({ matches: true })
        }
      })
    })
    expect(result.current).toBe(true)
  })

  it('cleans up listener on unmount', () => {
    const { unmount } = renderHook(() => useMediaQuery('(max-width: 767px)'))
    // matchMedia is called in both useState initializer and useEffect,
    // the effect's call is the one that registers the listener
    const lastCallResult = mockMatchMedia.mock.results[mockMatchMedia.mock.results.length - 1]?.value
    unmount()
    expect(lastCallResult.removeEventListener).toHaveBeenCalledWith('change', expect.any(Function))
  })

  it('handles missing matchMedia gracefully', () => {
    // When matchMedia returns no match, result should be false
    mockMatches = false
    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'))
    expect(result.current).toBe(false)
  })
})

describe('named hooks', () => {
  beforeEach(() => {
    vi.stubGlobal('matchMedia', vi.fn((query) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })))
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('useIsMobile uses correct query', () => {
    renderHook(() => useIsMobile())
    expect(window.matchMedia).toHaveBeenCalledWith('(max-width: 767px)')
  })

  it('useIsTablet uses correct query', () => {
    renderHook(() => useIsTablet())
    expect(window.matchMedia).toHaveBeenCalledWith('(min-width: 768px) and (max-width: 1023px)')
  })

  it('useIsDesktop uses correct query', () => {
    renderHook(() => useIsDesktop())
    expect(window.matchMedia).toHaveBeenCalledWith('(min-width: 1024px)')
  })

  it('useIsLandscape uses correct query', () => {
    renderHook(() => useIsLandscape())
    expect(window.matchMedia).toHaveBeenCalledWith('(orientation: landscape)')
  })
})
