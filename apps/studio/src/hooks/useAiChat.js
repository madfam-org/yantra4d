/**
 * Shared chat state management hook for AI Configurator and Code Editor.
 */
import { useState, useCallback, useRef } from 'react'
import { createSession, streamChat } from '../services/aiService'

export function useAiChat({ projectSlug, mode, params, setParams }) {
  const [messages, setMessages] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [pendingEdits, setPendingEdits] = useState([])
  const sessionIdRef = useRef(null)
  const abortRef = useRef(null)

  const initSession = useCallback(async () => {
    if (sessionIdRef.current) return sessionIdRef.current
    const sid = await createSession(projectSlug, mode)
    sessionIdRef.current = sid
    return sid
  }, [projectSlug, mode])

  const sendMessage = useCallback(async (text, fileContents = null) => {
    if (!text.trim() || isStreaming) return

    setMessages(prev => [...prev, { role: 'user', content: text }])
    setIsStreaming(true)
    setStreamingText('')

    try {
      const sid = await initSession()

      const context = mode === 'configurator'
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
            setParams(prev => ({ ...prev, ...event.changes }))
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
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
      setIsStreaming(false)
    }
  }, [isStreaming, initSession, mode, params, setParams])

  /**
   * Accept a pending code edit at the given index and remove it from the queue.
   * Used by the SCAD code editor to apply AI-suggested search/replace edits.
   * @param {number} index - index of the edit in the pendingEdits array
   */
  const applyEdit = useCallback((index) => {
    setPendingEdits(prev => prev.filter((_, i) => i !== index))
  }, [])

  /**
   * Reject a pending code edit at the given index and remove it from the queue.
   * Used by the SCAD code editor to dismiss AI-suggested edits.
   * @param {number} index - index of the edit in the pendingEdits array
   */
  const rejectEdit = useCallback((index) => {
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
