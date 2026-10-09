import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import {
  getQualityMode, getQualityReadings, getRenderScale, publishReadings, setQualityMode, setRenderScale, subscribeQuality,
  useQualityMode, useQualityReadings, useRenderScale,
} from './viewerQuality'

describe('mode store', () => {
  beforeEach(() => { localStorage.clear(); setQualityMode('auto') })

  it('persists the mode, ignores unknown values and notifies subscribers', () => {
    const listener = vi.fn()
    const off = subscribeQuality(listener)
    setQualityMode('battery')
    expect(getQualityMode()).toBe('battery')
    expect(localStorage.getItem('yantra4d-viewer-quality')).toBe('battery')
    setQualityMode('ultra')
    setQualityMode('battery')
    expect(listener).toHaveBeenCalledTimes(1)
    off()
  })

  it('keeps working when storage throws', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked') })
    setQualityMode('sharp')
    expect(getQualityMode()).toBe('sharp')
    spy.mockRestore()
  })

  it('exposes mode, scale and readings through hooks, skipping identical readings', () => {
    const mode = renderHook(() => useQualityMode())
    const scale = renderHook(() => useRenderScale())
    const readings = renderHook(() => useQualityReadings())
    act(() => { setQualityMode('balanced'); setRenderScale(0.75) })
    expect(mode.result.current).toBe('balanced')
    expect(scale.result.current).toBe(0.75)
    expect(getRenderScale()).toBe(0.75)
    const next = { ...getQualityReadings(), fps: 42 }
    act(() => publishReadings(next))
    expect(readings.result.current.fps).toBe(42)
    act(() => publishReadings({ ...next }))
    expect(getQualityReadings()).toBe(next)
    act(() => setRenderScale(1))
  })
})

