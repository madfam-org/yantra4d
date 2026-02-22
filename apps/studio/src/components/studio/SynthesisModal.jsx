import React, { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Sparkles, Loader2, CheckCircle2, XCircle, X } from 'lucide-react'

export default function SynthesisModal({ open, onOpenChange, onSynthesisComplete }) {
  const [prompt, setPrompt] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [logs, setLogs] = useState([])
  const [error, setError] = useState(null)

  const handleSynthesize = async () => {
    if (!prompt.trim()) return

    setIsGenerating(true)
    setLogs([])
    setError(null)
    setLogs(prev => [...prev, "Initiating Hyperobject Synthesis Engine..."])

    try {
      // 1. Send the POST request to start the SSE stream
      const baseUrl = import.meta.env.VITE_API_BASE || ''
      const token = localStorage.getItem('yantra4d_token')
      
      const response = await fetch(`${baseUrl}/api/ai/synthesize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ prompt })
      })

      if (!response.ok) {
        throw new Error(`Failed to start synthesis: ${response.statusText}`)
      }

      // 2. Read the SSE stream
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6)
            try {
              const data = JSON.parse(dataStr)
              
              if (data.event === 'chunk') {
                // Stream output directly to logs
                setLogs(prev => {
                  const newLogs = [...prev]
                  if (newLogs.length > 0 && !newLogs[newLogs.length - 1].startsWith("✓")) {
                    newLogs[newLogs.length - 1] += data.text
                  } else {
                    newLogs.push(data.text)
                  }
                  return newLogs
                })
              } else if (data.event === 'cartridge') {
                setLogs(prev => [...prev, `\n✓ Cartridge Generated: ${data.slug}`])
                
                // Wait briefly for UX, then handle completion
                setTimeout(() => {
                  onSynthesisComplete(data.slug)
                  onOpenChange(false)
                  setIsGenerating(false)
                  setPrompt('')
                  setLogs([])
                }, 1500)
                
              } else if (data.event === 'error') {
                throw new Error(data.error)
              }
            } catch (e) {
              console.error("Failed to parse SSE event:", e, dataStr)
            }
          }
        }
      }

    } catch (err) {
      console.error(err)
      setError(err.message || 'An unexpected error occurred during synthesis.')
      setIsGenerating(false)
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="bg-background border border-border shadow-lg rounded-lg w-full max-w-lg flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div>
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-500" />
              Hyperobject Synthesis Engine
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Describe the parametric cartridge you want to build. The AI will generate the manifest and code.
            </p>
          </div>
          <button 
            onClick={() => !isGenerating && onOpenChange(false)} 
            className="text-muted-foreground hover:text-foreground disabled:opacity-50"
            disabled={isGenerating}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex flex-col gap-4 p-6 flex-1 overflow-hidden">
          {!isGenerating && logs.length === 0 ? (
            <textarea
              placeholder="e.g. Generate a stackable slide-holder box measuring 100x50x20mm..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="flex min-h-[150px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 resize-none"
            />
          ) : (
            <div className="flex-1 bg-black text-green-400 p-4 rounded-md font-mono text-xs whitespace-pre-wrap min-h-[200px] overflow-y-auto">
              {logs.map((log, i) => (
                <span key={i}>{log}</span>
              ))}
              {isGenerating && <span className="animate-pulse">_</span>}
            </div>
          )}

          {error && (
            <div className="p-3 bg-destructive/10 text-destructive rounded-md flex items-center gap-2 text-sm">
              <XCircle className="w-4 h-4 shrink-0" />
              <p>{error}</p>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 p-6 pt-2">
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={isGenerating}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSynthesize}
            disabled={isGenerating || !prompt.trim()}
            className="bg-purple-600 hover:bg-purple-700 text-white"
          >
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Synthesizing...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                Generate Cartridge
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
