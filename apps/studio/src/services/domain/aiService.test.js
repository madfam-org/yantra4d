import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../core/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('../core/apiClient', () => ({
  apiFetch: vi.fn(),
}))

import { createSession, streamChat } from './aiService'
import { apiFetch } from '../core/apiClient'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('createSession', () => {
  it('calls POST /api/ai/session and returns session_id', async () => {
    apiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ session_id: 'abc-123' }),
    })
    const sid = await createSession('my-project', 'configurator')
    expect(sid).toBe('abc-123')
    expect(apiFetch).toHaveBeenCalledWith(
      'http://localhost:5000/api/ai/session',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ project: 'my-project', mode: 'configurator' }),
      }),
    )
  })

  it('throws on error response', async () => {
    apiFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'AI not configured' }),
    })
    await expect(createSession('p', 'configurator')).rejects.toThrow('AI not configured')
  })
})

describe('streamChat', () => {
  it('calls onChunk and onDone for SSE events', async () => {
    const sseData = [
      'data: {"event":"chunk","text":"Hello"}\n\n',
      'data: {"event":"chunk","text":" world"}\n\n',
      'data: {"event":"done"}\n\n',
    ].join('')

    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(sseData))
        controller.close()
      },
    })

    apiFetch.mockResolvedValue({
      ok: true,
      body: stream,
    })

    const onChunk = vi.fn()
    const onDone = vi.fn()
    const onResult = vi.fn()

    streamChat('sid-1', 'hello', {}, { onChunk, onDone, onResult })

    // Wait for async processing
    await new Promise(r => setTimeout(r, 50))

    expect(onChunk).toHaveBeenCalledWith('Hello')
    expect(onChunk).toHaveBeenCalledWith(' world')
    expect(onDone).toHaveBeenCalled()
  })

  it('calls onResult for params event', async () => {
    const sseData = 'data: {"event":"params","changes":{"width":50}}\n\ndata: {"event":"done"}\n\n'
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(sseData))
        controller.close()
      },
    })

    apiFetch.mockResolvedValue({ ok: true, body: stream })

    const onResult = vi.fn()
    const onDone = vi.fn()

    streamChat('sid-1', 'wider', {}, { onResult, onDone })
    await new Promise(r => setTimeout(r, 50))

    expect(onResult).toHaveBeenCalledWith({ event: 'params', changes: { width: 50 } })
  })

  it('calls onError for SSE error event', async () => {
    const sseData = 'data: {"event":"error","error":"Model overloaded"}\n\n'
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(sseData))
        controller.close()
      },
    })
    apiFetch.mockResolvedValue({ ok: true, body: stream })
    const onError = vi.fn()
    const onDone = vi.fn()
    streamChat('sid-1', 'hi', {}, { onError, onDone })
    await new Promise(r => setTimeout(r, 50))
    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ message: 'Model overloaded' }))
  })

  it('calls onResult for edits event', async () => {
    const sseData = 'data: {"event":"edits","edits":[{"file":"a.scad"}]}\n\ndata: {"event":"done"}\n\n'
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(sseData))
        controller.close()
      },
    })
    apiFetch.mockResolvedValue({ ok: true, body: stream })
    const onResult = vi.fn()
    streamChat('sid-1', 'edit', {}, { onResult })
    await new Promise(r => setTimeout(r, 50))
    expect(onResult).toHaveBeenCalledWith(expect.objectContaining({ event: 'edits' }))
  })

  it('does not call onError for AbortError', async () => {
    apiFetch.mockRejectedValue(new DOMException('Aborted', 'AbortError'))
    const onError = vi.fn()
    streamChat('sid-1', 'hi', {}, { onError })
    await new Promise(r => setTimeout(r, 50))
    expect(onError).not.toHaveBeenCalled()
  })

  it('skips malformed SSE lines', async () => {
    const sseData = 'data: INVALID JSON\n\ndata: {"event":"done"}\n\n'
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(sseData))
        controller.close()
      },
    })
    apiFetch.mockResolvedValue({ ok: true, body: stream })
    const onDone = vi.fn()
    streamChat('sid-1', 'hi', {}, { onDone })
    await new Promise(r => setTimeout(r, 50))
    expect(onDone).toHaveBeenCalled()
  })

  it('returns abort function', () => {
    apiFetch.mockResolvedValue({ ok: true, body: new ReadableStream() })
    const abort = streamChat('sid-1', 'hi', {}, {})
    expect(typeof abort).toBe('function')
  })

  it('calls onError on HTTP failure', async () => {
    apiFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Rate limited' }),
    })

    const onError = vi.fn()
    streamChat('sid-1', 'hello', {}, { onError })
    await new Promise(r => setTimeout(r, 50))

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ message: 'Rate limited' }))
  })
})
