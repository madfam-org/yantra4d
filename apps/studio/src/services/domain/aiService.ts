/**
 * AI chat API client — session creation and SSE streaming.
 */
import { getApiBase } from '../core/backendDetection'
import { apiFetch } from '../core/apiClient'

const base = (): string => getApiBase()

export async function createSession(project: string, mode: string): Promise<string> {
  const res = await apiFetch(`${base()}/api/ai/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project, mode }),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to create AI session')
  const data = await res.json()
  return data.session_id
}

interface StreamChatEvent {
  event: string
  text?: string
  changes?: Record<string, unknown>
  edits?: CodeEdit[]
  error?: string
}

interface CodeEdit {
  file: string
  search: string
  replace: string
}

interface StreamChatCallbacks {
  onChunk?: (text: string) => void
  onResult?: (event: StreamChatEvent) => void
  onDone?: () => void
  onError?: (err: Error) => void
}

/**
 * Stream chat responses via SSE.
 * Returns an abort function.
 */
export function streamChat(
  sessionId: string,
  message: string,
  context: Record<string, unknown>,
  { onChunk, onResult, onDone, onError }: StreamChatCallbacks
): () => void {
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

      const reader = res.body!.getReader()
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
            const event: StreamChatEvent = JSON.parse(line.slice(6))
            if (event.event === 'chunk') {
              onChunk?.(event.text || '')
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
      if ((err as Error).name !== 'AbortError') {
        onError?.(err as Error)
      }
    }
  })()

  return () => controller.abort()
}
