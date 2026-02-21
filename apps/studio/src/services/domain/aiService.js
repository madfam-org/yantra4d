/**
 * AI chat API client — session creation and SSE streaming.
 */
import { getApiBase } from '../core/backendDetection'
import { apiFetch } from '../core/apiClient'

const base = () => getApiBase()

export async function createSession(project, mode) {
  const res = await apiFetch(`${base()}/api/ai/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project, mode }),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to create AI session')
  const data = await res.json()
  return data.session_id
}

/**
 * Stream chat responses via SSE.
 * @param {string} sessionId
 * @param {string} message
 * @param {object} context - { current_params } for configurator, { file_contents } for code-editor
 * @param {{ onChunk, onResult, onDone, onError }} callbacks
 * @returns {() => void} abort function
 */
export function streamChat(sessionId, message, context, { onChunk, onResult, onDone, onError }) {
  const controller = new AbortController()

  ;(async () => {
    try {
      const res = await apiFetch(`${base()}/api/ai/chat-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message, ...context }),
        signal: controller.signal,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: 'Stream failed' }))
        onError?.(new Error(err.error || `HTTP ${res.status}`))
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            if (event.event === 'chunk') {
              onChunk?.(event.text)
            } else if (event.event === 'params' || event.event === 'edits') {
              onResult?.(event)
            } else if (event.event === 'done') {
              onDone?.()
            } else if (event.event === 'error') {
              onError?.(new Error(event.error))
            }
          } catch {
            // skip malformed lines
          }
        }
      }
      onDone?.()
    } catch (err) {
      if (err.name !== 'AbortError') {
        onError?.(err)
      }
    }
  })()

  return () => controller.abort()
}
