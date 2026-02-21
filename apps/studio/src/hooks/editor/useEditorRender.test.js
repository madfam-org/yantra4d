import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

vi.mock('../../services/domain/editorService', () => ({
  writeFile: vi.fn().mockResolvedValue({ path: 'main.scad', size: 10 }),
}))

import { useEditorRender } from './useEditorRender'
import { writeFile } from '../../services/domain/editorService'

beforeEach(() => {
  vi.clearAllMocks()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useEditorRender', () => {
  it('saveAndRender debounces writes', async () => {
    const handleGenerate = vi.fn()
    const { result } = renderHook(() => useEditorRender({ slug: 'proj', handleGenerate }))

    act(() => {
      result.current.saveAndRender('main.scad', 'cube(10);')
      result.current.saveAndRender('main.scad', 'cube(20);')
    })

    // Before debounce fires
    expect(writeFile).not.toHaveBeenCalled()

    // Advance past debounce (800ms)
    await act(async () => {
      vi.advanceTimersByTime(900)
      await Promise.resolve()
    })

    expect(writeFile).toHaveBeenCalledTimes(1)
    expect(writeFile).toHaveBeenCalledWith('proj', 'main.scad', 'cube(20);')
  })

  it('saveImmediate writes without debounce', async () => {
    const handleGenerate = vi.fn()
    const { result } = renderHook(() => useEditorRender({ slug: 'proj', handleGenerate }))

    await act(async () => {
      await result.current.saveImmediate('main.scad', 'cube(10);')
    })

    expect(writeFile).toHaveBeenCalledWith('proj', 'main.scad', 'cube(10);')
  })

  it('cancel clears pending debounce', () => {
    const handleGenerate = vi.fn()
    const { result } = renderHook(() => useEditorRender({ slug: 'proj', handleGenerate }))

    act(() => {
      result.current.saveAndRender('main.scad', 'cube(10);')
      result.current.cancel()
    })

    act(() => {
      vi.advanceTimersByTime(1000)
    })

    expect(writeFile).not.toHaveBeenCalled()
  })

  it('saveImmediate cancels pending debounce', async () => {
    const handleGenerate = vi.fn()
    const { result } = renderHook(() => useEditorRender({ slug: 'proj', handleGenerate }))

    act(() => {
      result.current.saveAndRender('main.scad', 'old content')
    })

    await act(async () => {
      await result.current.saveImmediate('main.scad', 'new content')
    })

    act(() => {
      vi.advanceTimersByTime(1000)
    })

    // Only the immediate write
    expect(writeFile).toHaveBeenCalledTimes(1)
    expect(writeFile).toHaveBeenCalledWith('proj', 'main.scad', 'new content')
  })
})
