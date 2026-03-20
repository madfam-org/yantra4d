/**
 * Shared chat state management hook for AI Configurator and Code Editor.
 */
import { useState, useCallback, useRef } from 'react'
import { createSession, streamChat } from '../../services/domain/aiService'

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  changes?: Record<string, unknown>
}

interface CodeEdit {
  file: string
  search: string
  replace: string
}

interface UseAiChatOptions {
  projectSlug: string
  mode: string
  params: Record<string, unknown>
  setParams?: (updater: (prev: Record<string, unknown>) => Record<string, unknown>) => void
}

interface UseAiChatResult {
  messages: ChatMessage[]
  sendMessage: (text: string, fileContents?: Record<string, string> | null) => Promise<void>
  isStreaming: boolean
  streamingText: string
  pendingEdits: CodeEdit[]
  setPendingEdits: React.Dispatch<React.SetStateAction<CodeEdit[]>>
  applyEdit: (index: number) => void
  rejectEdit: (index: number) => void
  resetSession: () => void
}

export function useAiChat({ projectSlug, mode, params, setParams }: UseAiChatOptions): UseAiChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [pendingEdits, setPendingEdits] = useState<CodeEdit[]>([])
  const sessionIdRef = useRef<string | null>(null)
  const abortRef = useRef<(() => void) | null>(null)

  const initSession = useCallback(async (): Promise<string> => {
    if (sessionIdRef.current) return sessionIdRef.current
    const sid = await createSession(projectSlug, mode)
    sessionIdRef.current = sid
    return sid
  }, [projectSlug, mode])

  const sendMessage = useCallback(async (text: string, fileContents: Record<string, string> | null = null) => {
    if (!text.trim() || isStreaming) return

    setMessages(prev => [...prev, { role: 'user', content: text }])
    setIsStreaming(true)
    setStreamingText('')

    try {
      const sid = await initSession()

      const context: Record<string, unknown> = mode === 'configurator'
        ? { current_params: params }
        : { file_contents: fileContents || {} }

      let fullText = ''

      abortRef.current = streamChat(sid, text, context, {
        onChunk(chunk) {
          fullText += chunk
          setStreamingText(fullText)
        },
        onResult(event) {
          if (event.event === 'params' && event.changes && setParams) {
            setParams(prev => ({ ...prev, ...event.changes! }))
            setMessages(prev => [
              ...prev,
              { role: 'system', content: 'params', changes: event.changes },
            ])
          }
          if (event.event === 'edits' && event.edits) {
            setPendingEdits(event.edits)
          }
        },
        onDone() {
          if (fullText) {
            setMessages(prev => [...prev, { role: 'assistant', content: fullText }])
          }
          setStreamingText('')
          setIsStreaming(false)
        },
        onError(err) {
          setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
          setStreamingText('')
          setIsStreaming(false)
        },
      })
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${(err as Error).message}` }])
      setIsStreaming(false)
    }
  }, [isStreaming, initSession, mode, params, setParams])

  /**
   * Accept a pending code edit at the given index and remove it from the queue.
   * Used by the SCAD code editor to apply AI-suggested search/replace edits.
   */
  const applyEdit = useCallback((index: number) => {
    setPendingEdits(prev => prev.filter((_, i) => i !== index))
  }, [])

  /**
   * Reject a pending code edit at the given index and remove it from the queue.
   * Used by the SCAD code editor to dismiss AI-suggested edits.
   */
  const rejectEdit = useCallback((index: number) => {
    setPendingEdits(prev => prev.filter((_, i) => i !== index))
  }, [])

  const resetSession = useCallback(() => {
    if (abortRef.current) abortRef.current()
    sessionIdRef.current = null
    setMessages([])
    setStreamingText('')
    setPendingEdits([])
    setIsStreaming(false)
  }, [])

  return {
    messages,
    sendMessage,
    isStreaming,
    streamingText,
    pendingEdits,
    setPendingEdits,
    applyEdit,
    rejectEdit,
    resetSession,
  }
}
