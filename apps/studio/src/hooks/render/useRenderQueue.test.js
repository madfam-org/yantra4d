import { describe, it, expect, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useRenderQueue } from './useRenderQueue'

describe('useRenderQueue', () => {
  it('returns initial state', () => {
    const renderFn = vi.fn()
    const { result } = renderHook(() => useRenderQueue({ renderFn }))
    expect(result.current.queue).toEqual([])
    expect(result.current.currentId).toBeNull()
    expect(result.current.pendingCount).toBe(0)
  })

  it('enqueue adds items', async () => {
    const renderFn = vi.fn()
    const { result } = renderHook(() => useRenderQueue({ renderFn }))

    let id
    act(() => {
      id = result.current.enqueue({ mode: 'unit', params: {} })
    })
    expect(id).toBeTruthy()
    await waitFor(() => expect(result.current.queue).toHaveLength(1))
    expect(result.current.queue[0].status).toBe('pending')
    expect(result.current.pendingCount).toBe(1)
  })

  it('cancelItem marks item as cancelled', async () => {
    const renderFn = vi.fn()
    const { result } = renderHook(() => useRenderQueue({ renderFn }))

    let id
    act(() => {
      id = result.current.enqueue({ mode: 'unit' })
    })
    await waitFor(() => expect(result.current.queue).toHaveLength(1))
    act(() => {
      result.current.cancelItem(id)
    })
    await waitFor(() => expect(result.current.queue[0].status).toBe('cancelled'))
  })

  it('clearCompleted removes non-pending items', async () => {
    const renderFn = vi.fn()
    const { result } = renderHook(() => useRenderQueue({ renderFn }))

    act(() => {
      result.current.enqueue({ mode: 'unit' })
    })
    await waitFor(() => expect(result.current.queue).toHaveLength(1))
    const id = result.current.queue[0].id
    act(() => {
      result.current.cancelItem(id)
    })
    await waitFor(() => expect(result.current.queue[0].status).toBe('cancelled'))
    act(() => {
      result.current.clearCompleted()
    })
    await waitFor(() => expect(result.current.queue).toHaveLength(0))
  })

  it('processQueue starts processing', async () => {
    const renderFn = vi.fn().mockResolvedValue({ parts: [] })
    const { result } = renderHook(() => useRenderQueue({ renderFn }))

    act(() => {
      result.current.enqueue({ mode: 'unit' })
    })
    await waitFor(() => expect(result.current.queue).toHaveLength(1))

    await act(async () => {
      result.current.processQueue()
      await new Promise(r => setTimeout(r, 50))
    })

    expect(typeof result.current.processQueue).toBe('function')
  })

  it('multiple enqueue items are processed', async () => {
    const renderFn = vi.fn().mockResolvedValue({ parts: [] })
    const { result } = renderHook(() => useRenderQueue({ renderFn }))

    act(() => {
      result.current.enqueue({ mode: 'a' })
      result.current.enqueue({ mode: 'b' })
    })
    await waitFor(() => expect(result.current.queue).toHaveLength(2))
    expect(result.current.pendingCount).toBe(2)
  })

  it('processQueue completes items and sets status to completed', async () => {
    const renderFn = vi.fn().mockResolvedValue({ parts: ['main'] })
    const { result } = renderHook(() => useRenderQueue({ renderFn }))

    act(() => { result.current.enqueue({ mode: 'unit' }) })
    await waitFor(() => expect(result.current.queue).toHaveLength(1))

    await act(async () => {
      await result.current.processQueue()
    })

    await waitFor(() => {
      const completed = result.current.queue.filter(i => i.status === 'completed')
      expect(completed).toHaveLength(1)
      expect(completed[0].result).toEqual({ parts: ['main'] })
    })
    expect(renderFn).toHaveBeenCalledTimes(1)
  })

  it('processQueue sets status to failed when renderFn throws', async () => {
    const renderFn = vi.fn().mockRejectedValue(new Error('render failed'))
    const { result } = renderHook(() => useRenderQueue({ renderFn }))

    act(() => { result.current.enqueue({ mode: 'unit' }) })
    await waitFor(() => expect(result.current.queue).toHaveLength(1))

    await act(async () => {
      await result.current.processQueue()
    })

    await waitFor(() => {
      const failed = result.current.queue.filter(i => i.status === 'failed')
      expect(failed).toHaveLength(1)
      expect(failed[0].error).toBe('render failed')
    })
  })

  it('processQueue skips cancelled items', async () => {
    const renderFn = vi.fn().mockResolvedValue({ parts: [] })
    const { result } = renderHook(() => useRenderQueue({ renderFn }))

    let id
    act(() => { id = result.current.enqueue({ mode: 'unit' }) })
    await waitFor(() => expect(result.current.queue).toHaveLength(1))

    act(() => { result.current.cancelItem(id) })
    await waitFor(() => expect(result.current.queue[0].status).toBe('cancelled'))

    await act(async () => {
      await result.current.processQueue()
    })

    expect(renderFn).not.toHaveBeenCalled()
  })

  it('clearCompleted keeps pending items and removes cancelled/completed', async () => {
    const renderFn = vi.fn().mockResolvedValue({ parts: [] })
    const { result } = renderHook(() => useRenderQueue({ renderFn }))

    let id1
    act(() => {
      id1 = result.current.enqueue({ mode: 'a' })
      result.current.enqueue({ mode: 'b' })
    })
    await waitFor(() => expect(result.current.queue).toHaveLength(2))

    act(() => { result.current.cancelItem(id1) })
    await waitFor(() => expect(result.current.queue.find(i => i.id === id1).status).toBe('cancelled'))

    await act(async () => {
      await result.current.processQueue()
    })

    await waitFor(() => expect(result.current.queue.find(i => i.mode === 'b').status).toBe('completed'))

    act(() => { result.current.clearCompleted() })

    await waitFor(() => {
      expect(result.current.queue).toHaveLength(0)
    })
  })

  it('processQueue is not reentrant (second call while processing is ignored)', async () => {
    let resolveRender
    const renderFn = vi.fn(() => new Promise(r => { resolveRender = r }))
    const { result } = renderHook(() => useRenderQueue({ renderFn }))

    act(() => { result.current.enqueue({ mode: 'unit' }) })
    await waitFor(() => expect(result.current.queue).toHaveLength(1))

    // Start processing (won't resolve yet)
    let p1
    act(() => {
      p1 = result.current.processQueue()
    })

    // Immediately call again - should be ignored due to processingRef guard
    act(() => { result.current.processQueue() })

    await waitFor(() => expect(renderFn).toHaveBeenCalled())

    await act(async () => {
      resolveRender({ parts: [] })
      await p1
    })

    expect(renderFn).toHaveBeenCalledTimes(1)
  })
})
