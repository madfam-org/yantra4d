import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

const calls = []
vi.mock('../../services/domain/editorService', () => ({
  writeFile: vi.fn(async (...args) => { calls.push(['writeFile', ...args]); return { size: 1 } }),
  updateGraphBindings: vi.fn(async (...args) => { calls.push(['updateGraphBindings', ...args]); return { bindings: { a: 'x.r' } } }),
}))

import { useGraphPersistence } from './useGraphPersistence'
import { writeFile, updateGraphBindings } from '../../services/domain/editorService'

beforeEach(() => {
  calls.length = 0
  vi.clearAllMocks()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

function setup(extra = {}) {
  const handleGenerate = vi.fn()
  const onBindingsSaved = vi.fn()
  const onSaved = vi.fn()
  const hook = renderHook(() => useGraphPersistence({ slug: 'fork', handleGenerate, onBindingsSaved, onSaved, ...extra }))
  return { hook, handleGenerate, onBindingsSaved, onSaved }
}

describe('useGraphPersistence', () => {
  it('writes the graph, then the bindings, then renders — in that order', async () => {
    const { hook, handleGenerate, onBindingsSaved, onSaved } = setup()
    await act(async () => {
      await hook.result.current.saveNow('part.graph.json', '{}', { a: 'x.r' })
    })
    expect(calls.map((c) => c[0])).toEqual(['writeFile', 'updateGraphBindings'])
    expect(writeFile).toHaveBeenCalledWith('fork', 'part.graph.json', '{}')
    expect(updateGraphBindings).toHaveBeenCalledWith('fork', { a: 'x.r' })
    expect(onBindingsSaved).toHaveBeenCalledWith({ bindings: { a: 'x.r' } })
    expect(onSaved).toHaveBeenCalledWith('part.graph.json', '{}')
    expect(handleGenerate).toHaveBeenCalledTimes(1)
    expect(hook.result.current.status).toBe('saved')
  })

  it('skips the bindings call when nothing changed', async () => {
    const { hook } = setup()
    await act(async () => {
      await hook.result.current.saveNow('part.graph.json', '{}', {})
      await hook.result.current.saveNow('part.graph.json', '{}', null)
    })
    expect(updateGraphBindings).not.toHaveBeenCalled()
  })

  it('debounces scheduled saves; the latest wins', async () => {
    const { hook } = setup()
    act(() => {
      hook.result.current.schedule('part.graph.json', 'one', null)
      hook.result.current.schedule('part.graph.json', 'two', null)
    })
    expect(hook.result.current.status).toBe('pending')
    expect(writeFile).not.toHaveBeenCalled()
    await act(async () => {
      vi.advanceTimersByTime(900)
    })
    expect(writeFile).toHaveBeenCalledTimes(1)
    expect(writeFile).toHaveBeenCalledWith('fork', 'part.graph.json', 'two')
  })

  it('cancel drops a pending save, and saveNow replaces it', async () => {
    const { hook } = setup()
    act(() => {
      hook.result.current.schedule('part.graph.json', 'stale', null)
      hook.result.current.cancel()
    })
    await act(async () => { vi.advanceTimersByTime(1000) })
    expect(writeFile).not.toHaveBeenCalled()

    act(() => hook.result.current.schedule('part.graph.json', 'stale', null))
    await act(async () => { await hook.result.current.saveNow('part.graph.json', 'fresh', null) })
    await act(async () => { vi.advanceTimersByTime(1000) })
    expect(writeFile).toHaveBeenCalledTimes(1)
    expect(writeFile).toHaveBeenCalledWith('fork', 'part.graph.json', 'fresh')
  })

  it('reports the server refusal and does not render', async () => {
    updateGraphBindings.mockRejectedValueOnce(new Error('parameter binds unknown node'))
    const { hook, handleGenerate, onSaved } = setup()
    let ok
    await act(async () => {
      ok = await hook.result.current.saveNow('part.graph.json', '{}', { a: 'ghost.r' })
    })
    expect(ok).toBe(false)
    expect(hook.result.current.status).toBe('error')
    expect(hook.result.current.error).toBe('parameter binds unknown node')
    expect(handleGenerate).not.toHaveBeenCalled()
    expect(onSaved).not.toHaveBeenCalled()
  })
})
