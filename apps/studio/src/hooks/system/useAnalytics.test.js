import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'

vi.mock('../../services/core/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

import { useAnalytics } from './useAnalytics'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useAnalytics', () => {
  it('returns track function', () => {
    const { result } = renderHook(() => useAnalytics('my-project'))
    expect(typeof result.current.track).toBe('function')
  })

  it('track uses sendBeacon when available', () => {
    const mockSendBeacon = vi.fn().mockReturnValue(true)
    vi.stubGlobal('navigator', { sendBeacon: mockSendBeacon })

    const { result } = renderHook(() => useAnalytics('my-project'))
    result.current.track('render', { mode: 'unit' })

    expect(mockSendBeacon).toHaveBeenCalledWith(
      'http://localhost:5000/api/analytics/track',
      expect.any(Blob)
    )
  })

  it('track falls back to fetch when sendBeacon is unavailable', () => {
    vi.stubGlobal('navigator', {})
    const mockFetch = vi.fn().mockResolvedValue({})
    vi.spyOn(globalThis, 'fetch').mockImplementation(mockFetch)

    const { result } = renderHook(() => useAnalytics('my-project'))
    result.current.track('export')

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:5000/api/analytics/track',
      expect.objectContaining({ method: 'POST', keepalive: true })
    )
  })

  it('track silently catches errors', () => {
    vi.stubGlobal('navigator', { sendBeacon: () => { throw new Error('fail') } })
    const { result } = renderHook(() => useAnalytics('my-project'))

    // Should not throw
    expect(() => result.current.track('render')).not.toThrow()
  })
})
