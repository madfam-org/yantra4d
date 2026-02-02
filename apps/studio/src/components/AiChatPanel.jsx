import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Send, RotateCcw, Loader2, Check, X } from 'lucide-react'
import { useAiChat } from '../hooks/useAiChat'

/**
 * Chat UI for AI Configurator and Code Editor modes.
 * @param {object} props
 * @param {"configurator"|"code-editor"} props.mode
 * @param {string} props.projectSlug
 * @param {object} props.manifest
 * @param {object} props.params - current parameter values (configurator)
 * @param {function} props.setParams - setter for params (configurator)
 * @param {function} props.onApplyEdits - callback for code-editor edits
 * @param {object} props.fileContents - current SCAD file contents (code-editor)
 */
export default function AiChatPanel({ mode, projectSlug, manifest, params, setParams, onApplyEdits, fileContents }) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)

  const {
    messages, sendMessage, isStreaming, streamingText,
    pendingEdits, setPendingEdits, resetSession,
  } = useAiChat({ projectSlug, mode, manifest, params, setParams })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  const handleSend = () => {
    if (!input.trim() || isStreaming) return
    sendMessage(input.trim(), fileContents)
    setInput('')
  }

  const handleApplyAll = () => {
    if (onApplyEdits && pendingEdits.length > 0) {
      onApplyEdits(pendingEdits)
      setPendingEdits([])
    }
  }

  const handleRejectAll = () => {
    setPendingEdits([])
  }

  return (
    <div className="flex flex-col h-full bg-card">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-border">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {mode === 'configurator' ? 'AI Configurator' : 'AI Code Editor'}
        </span>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={resetSession} title="New conversation">
          <RotateCcw className="h-3.5 w-3.5" />
          <span className="sr-only">New conversation</span>
        </Button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2 min-h-0">
        {messages.length === 0 && !isStreaming && (
          <p className="text-xs text-muted-foreground text-center py-4">
            {mode === 'configurator'
              ? 'Describe how you want to adjust the model...'
              : 'Describe the code changes you want...'}
          </p>
        )}
        {messages.map((msg, i) => {
          if (msg.role === 'system' && msg.content === 'params') {
            return (
              <div key={i} className="flex flex-wrap gap-1">
                {Object.entries(msg.changes || {}).map(([k, v]) => (
                  <span key={k} className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] rounded bg-primary/15 text-primary">
                    <Check className="h-2.5 w-2.5" /> {k} → {v}
                  </span>
                ))}
              </div>
            )
          }
          return (
            <div key={i} className={`text-xs leading-relaxed whitespace-pre-wrap rounded-lg px-2.5 py-1.5 max-w-[90%] ${
              msg.role === 'user'
                ? 'ml-auto bg-primary text-primary-foreground'
                : 'bg-muted text-foreground'
            }`}>
              {msg.content}
            </div>
          )
        })}
        {isStreaming && streamingText && (
          <div className="text-xs leading-relaxed whitespace-pre-wrap rounded-lg px-2.5 py-1.5 bg-muted text-foreground max-w-[90%]">
            {streamingText}
            <span className="inline-block w-1.5 h-3 bg-foreground/50 animate-pulse ml-0.5" />
          </div>
        )}
        {isStreaming && !streamingText && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" /> Thinking...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Pending edits banner (code-editor) */}
      {mode === 'code-editor' && pendingEdits.length > 0 && (
        <div className="flex items-center justify-between px-3 py-1.5 border-t border-border bg-yellow-500/10">
          <span className="text-xs font-medium text-yellow-700 dark:text-yellow-400">
            {pendingEdits.length} edit{pendingEdits.length > 1 ? 's' : ''} pending
          </span>
          <div className="flex items-center gap-1">
            <Button size="sm" className="h-6 text-[10px]" onClick={handleApplyAll}>
              <Check className="h-3 w-3 mr-0.5" /> Apply All
            </Button>
            <Button variant="ghost" size="sm" className="h-6 text-[10px]" onClick={handleRejectAll}>
              <X className="h-3 w-3 mr-0.5" /> Reject
            </Button>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="flex items-center gap-2 px-3 py-2 border-t border-border">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
          placeholder={mode === 'configurator' ? 'e.g. "make it wider"' : 'e.g. "add rounded corners"'}
          className="flex-1 px-2 py-1.5 text-xs rounded border border-border bg-background focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          disabled={isStreaming}
        />
        <Button size="icon" className="h-7 w-7" onClick={handleSend} disabled={!input.trim() || isStreaming}>
          <Send className="h-3.5 w-3.5" />
          <span className="sr-only">Send</span>
        </Button>
      </div>
    </div>
  )
}
