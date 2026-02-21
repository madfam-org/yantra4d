import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

vi.mock('../services/domain/aiService', () => ({
  createSession: vi.fn().mockResolvedValue('session-123'),
  streamChat: vi.fn(),
}))

import { useAiChat } from './useAiChat'
import { createSession, streamChat } from '../services/domain/aiService'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useAiChat', () => {
  it('returns initial state', () => {
    const { result } = renderHook(() => useAiChat({
      projectSlug: 'proj',
      mode: 'configurator',
      params: {},
      setParams: vi.fn(),
    }))

    expect(result.current.messages).toEqual([])
    expect(result.current.isStreaming).toBe(false)
    expect(result.current.streamingText).toBe('')
    expect(result.current.pendingEdits).toEqual([])
  })

  it('sendMessage adds user message and starts streaming', async () => {
    streamChat.mockImplementation((sid, text, ctx, handlers) => {
      handlers.onChunk('Hello')
      handlers.onDone()
      return { abort: vi.fn() }
    })

    const { result } = renderHook(() => useAiChat({
      projectSlug: 'proj',
      mode: 'configurator',
      params: { width: 50 },
      setParams: vi.fn(),
    }))

    await act(async () => {
      await result.current.sendMessage('make it bigger')
    })

    expect(createSession).toHaveBeenCalledWith('proj', 'configurator')
    expect(result.current.messages.length).toBeGreaterThanOrEqual(2) // user + assistant
  })

  it('ignores empty messages', async () => {
    const { result } = renderHook(() => useAiChat({
      projectSlug: 'proj',
      mode: 'configurator',
      params: {},
      setParams: vi.fn(),
    }))

    await act(async () => {
      await result.current.sendMessage('   ')
    })

    expect(createSession).not.toHaveBeenCalled()
    expect(result.current.messages).toEqual([])
  })

  it('handles params event in configurator mode', async () => {
    const setParams = vi.fn()
    streamChat.mockImplementation((sid, text, ctx, handlers) => {
      handlers.onChunk('Setting width to 80')
      handlers.onResult({ event: 'params', changes: { width: 80 } })
      handlers.onDone()
      return { abort: vi.fn() }
    })

    const { result } = renderHook(() => useAiChat({
      projectSlug: 'proj',
      mode: 'configurator',
      params: { width: 50 },
      setParams,
    }))

    await act(async () => {
      await result.current.sendMessage('make it wider')
    })

    expect(setParams).toHaveBeenCalled()
  })

  it('handles edits event in editor mode', async () => {
    streamChat.mockImplementation((sid, text, ctx, handlers) => {
      handlers.onChunk('Updated code')
      handlers.onResult({ event: 'edits', edits: [{ file: 'main.scad', search: 'old', replace: 'new' }] })
      handlers.onDone()
      return { abort: vi.fn() }
    })

    const { result } = renderHook(() => useAiChat({
      projectSlug: 'proj',
      mode: 'editor',
      params: {},
      setParams: vi.fn(),
    }))

    await act(async () => {
      await result.current.sendMessage('change the code', { 'main.scad': 'old code' })
    })

    expect(result.current.pendingEdits).toHaveLength(1)
  })

  it('handles onError from streaming', async () => {
    streamChat.mockImplementation((sid, text, ctx, handlers) => {
      handlers.onError(new Error('Stream broke'))
      return { abort: vi.fn() }
    })

    const { result } = renderHook(() => useAiChat({
      projectSlug: 'proj',
      mode: 'configurator',
      params: {},
      setParams: vi.fn(),
    }))

    await act(async () => {
      await result.current.sendMessage('test')
    })

    expect(result.current.isStreaming).toBe(false)
    const lastMsg = result.current.messages[result.current.messages.length - 1]
    expect(lastMsg.content).toContain('Stream broke')
  })

  it('resetSession clears state and aborts', async () => {
    const abortFn = vi.fn()
    streamChat.mockImplementation((sid, text, ctx, handlers) => {
      handlers.onDone()
      return abortFn
    })

    const { result } = renderHook(() => useAiChat({
      projectSlug: 'proj',
      mode: 'configurator',
      params: {},
      setParams: vi.fn(),
    }))

    await act(async () => {
      await result.current.sendMessage('hello')
    })

    act(() => {
      result.current.resetSession()
    })

    expect(abortFn).toHaveBeenCalled()
    expect(result.current.messages).toEqual([])
    expect(result.current.pendingEdits).toEqual([])
    expect(result.current.isStreaming).toBe(false)
  })

  it('applyEdit removes edit at index', async () => {
    streamChat.mockImplementation((sid, text, ctx, handlers) => {
      handlers.onResult({ event: 'edits', edits: [{ file: 'a.scad' }, { file: 'b.scad' }] })
      handlers.onDone()
      return { abort: vi.fn() }
    })

    const { result } = renderHook(() => useAiChat({
      projectSlug: 'proj',
      mode: 'editor',
      params: {},
      setParams: vi.fn(),
    }))

    await act(async () => {
      await result.current.sendMessage('edit code')
    })

    expect(result.current.pendingEdits).toHaveLength(2)

    act(() => {
      result.current.applyEdit(0)
    })
    expect(result.current.pendingEdits).toHaveLength(1)
    expect(result.current.pendingEdits[0].file).toBe('b.scad')
  })

  it('rejectEdit removes edit at index', async () => {
    streamChat.mockImplementation((sid, text, ctx, handlers) => {
      handlers.onResult({ event: 'edits', edits: [{ file: 'a.scad' }] })
      handlers.onDone()
      return { abort: vi.fn() }
    })

    const { result } = renderHook(() => useAiChat({
      projectSlug: 'proj',
      mode: 'editor',
      params: {},
      setParams: vi.fn(),
    }))

    await act(async () => {
      await result.current.sendMessage('edit code')
    })

    act(() => {
      result.current.rejectEdit(0)
    })
    expect(result.current.pendingEdits).toHaveLength(0)
  })

  it('reuses existing session', async () => {
    streamChat.mockImplementation((sid, text, ctx, handlers) => {
      handlers.onDone()
      return { abort: vi.fn() }
    })

    const { result } = renderHook(() => useAiChat({
      projectSlug: 'proj',
      mode: 'configurator',
      params: {},
      setParams: vi.fn(),
    }))

    await act(async () => {
      await result.current.sendMessage('first')
    })
    await act(async () => {
      await result.current.sendMessage('second')
    })

    // createSession only called once
    expect(createSession).toHaveBeenCalledTimes(1)
  })

  it('handles errors gracefully', async () => {
    createSession.mockRejectedValue(new Error('AI unavailable'))

    const { result } = renderHook(() => useAiChat({
      projectSlug: 'proj',
      mode: 'configurator',
      params: {},
      setParams: vi.fn(),
    }))

    await act(async () => {
      await result.current.sendMessage('hello')
    })

    expect(result.current.isStreaming).toBe(false)
    const lastMsg = result.current.messages[result.current.messages.length - 1]
    expect(lastMsg.content).toContain('Error')
  })
})
