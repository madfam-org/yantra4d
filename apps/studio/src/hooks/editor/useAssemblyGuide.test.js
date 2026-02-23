import { describe, it, expect, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useAssemblyGuide } from './useAssemblyGuide'

describe('useAssemblyGuide', () => {
  function renderGuide(viewerRef = { current: null }) {
    return renderHook(() => useAssemblyGuide(viewerRef))
  }

  it('returns initial state', () => {
    const { result } = renderGuide()
    expect(result.current.assemblyActive).toBe(false)
    expect(result.current.highlightedParts).toEqual([])
    expect(result.current.visibleParts).toEqual([])
    expect(result.current.assemblyEditorOpen).toBe(false)
  })

  it('handleHighlightParts sets parts array', () => {
    const { result } = renderGuide()
    act(() => {
      result.current.handleHighlightParts(['body', 'lid'])
    })
    expect(result.current.highlightedParts).toEqual(['body', 'lid'])
  })

  it('handleHighlightParts with null sets empty array', () => {
    const { result } = renderGuide()
    act(() => {
      result.current.handleHighlightParts(null)
    })
    expect(result.current.highlightedParts).toEqual([])
  })

  it('handleAssemblyStepChange with null deactivates assembly', () => {
    const { result } = renderGuide()
    // First activate
    act(() => {
      result.current.handleAssemblyStepChange({ visible_parts: ['a'], highlight_parts: ['b'] })
    })
    expect(result.current.assemblyActive).toBe(true)

    // Then deactivate with null
    act(() => {
      result.current.handleAssemblyStepChange(null)
    })
    expect(result.current.assemblyActive).toBe(false)
    expect(result.current.highlightedParts).toEqual([])
    expect(result.current.visibleParts).toEqual([])
  })

  it('handleAssemblyStepChange with step activates and sets parts', () => {
    const { result } = renderGuide()
    act(() => {
      result.current.handleAssemblyStepChange({
        visible_parts: ['body'],
        highlight_parts: ['lid'],
      })
    })
    expect(result.current.assemblyActive).toBe(true)
    expect(result.current.visibleParts).toEqual(['body'])
    expect(result.current.highlightedParts).toEqual(['lid'])
  })

  it('handleAssemblyStepChange with camera calls animateTo', () => {
    const animateTo = vi.fn()
    const viewerRef = { current: { animateTo } }
    const { result } = renderGuide(viewerRef)
    act(() => {
      result.current.handleAssemblyStepChange({
        visible_parts: [],
        highlight_parts: [],
        camera: [10, 20, 30],
        camera_target: [0, 0, 0],
      })
    })
    expect(animateTo).toHaveBeenCalledWith([10, 20, 30], [0, 0, 0])
  })

  it('handleAssemblyStepChange without camera does not call animateTo', () => {
    const animateTo = vi.fn()
    const viewerRef = { current: { animateTo } }
    const { result } = renderGuide(viewerRef)
    act(() => {
      result.current.handleAssemblyStepChange({
        visible_parts: ['x'],
        highlight_parts: [],
      })
    })
    expect(animateTo).not.toHaveBeenCalled()
  })

  it('handleSetAssemblyCamera calls viewerRef.animateTo', () => {
    const animateTo = vi.fn()
    const viewerRef = { current: { animateTo } }
    const { result } = renderGuide(viewerRef)
    act(() => {
      result.current.handleSetAssemblyCamera([1, 2, 3], [4, 5, 6])
    })
    expect(animateTo).toHaveBeenCalledWith([1, 2, 3], [4, 5, 6])
  })

  it('handleSetAssemblyCamera with null viewerRef is safe', () => {
    const viewerRef = { current: null }
    const { result } = renderGuide(viewerRef)
    // Should not throw
    act(() => {
      result.current.handleSetAssemblyCamera([1, 2, 3], [4, 5, 6])
    })
  })

  it('setAssemblyEditorOpen toggles editor state', () => {
    const { result } = renderGuide()
    act(() => {
      result.current.setAssemblyEditorOpen(true)
    })
    expect(result.current.assemblyEditorOpen).toBe(true)
    act(() => {
      result.current.setAssemblyEditorOpen(false)
    })
    expect(result.current.assemblyEditorOpen).toBe(false)
  })

  it('step without visible_parts defaults to empty array', () => {
    const { result } = renderGuide()
    act(() => {
      result.current.handleAssemblyStepChange({
        // no visible_parts or highlight_parts
      })
    })
    expect(result.current.visibleParts).toEqual([])
    expect(result.current.highlightedParts).toEqual([])
  })
})
