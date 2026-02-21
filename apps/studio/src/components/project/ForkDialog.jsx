import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Loader2, GitFork } from 'lucide-react'
import { getApiBase } from '../../services/core/backendDetection'
import { apiFetch } from '../../services/core/apiClient'
import { validateSlug, sanitizeSlug } from '../../lib/slugUtils'

/**
 * Fork-to-edit modal for built-in projects.
 * @param {object} props
 * @param {string} props.slug - source project slug
 * @param {string} props.projectName - display name
 * @param {function} props.onClose - close callback
 * @param {function} props.onForked - callback with new slug after fork
 */
export default function ForkDialog({ slug, projectName, onClose, onForked }) {
  const [newSlug, setNewSlug] = useState(`my-${slug}`)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const slugError = validateSlug(newSlug)
  const isValid = !slugError

  const handleFork = async () => {
    if (!isValid || loading) return
    setLoading(true)
    setError(null)
    try {
      const res = await apiFetch(`${getApiBase()}/api/projects/${slug}/fork`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_slug: newSlug }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Fork failed')
      onForked(data.slug)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  return (
    <div // eslint-disable-line jsx-a11y/no-static-element-interactions, jsx-a11y/click-events-have-key-events
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions */}
      <div role="dialog" aria-modal="true" aria-label="Fork project" className="bg-card rounded-lg border border-border shadow-lg p-6 max-w-md w-full mx-4" onClick={e => e.stopPropagation()} onKeyDown={e => { if (e.key === 'Escape') onClose() }}>
        <div className="flex items-center gap-2 mb-4">
          <GitFork className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">Fork Project</h2>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Create your own editable copy of <strong>{projectName}</strong>.
        </p>
        <label htmlFor="fork-slug" className="block text-sm font-medium mb-1">Project slug</label>
        <input
          id="fork-slug"
          type="text"
          value={newSlug}
          onChange={e => setNewSlug(sanitizeSlug(e.target.value))}
          className="w-full px-3 py-2 text-sm rounded border border-border bg-background focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring mb-1"
          placeholder="my-project-name"
        />
        {!isValid && newSlug && (
          <p className="text-xs text-destructive mb-2">3-50 chars, lowercase alphanumeric with hyphens</p>
        )}
        {error && (
          <p className="text-xs text-destructive mb-2">{error}</p>
        )}
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="ghost" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button onClick={handleFork} disabled={!isValid || loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <GitFork className="h-4 w-4 mr-1" />}
            Fork & Edit
          </Button>
        </div>
      </div>
    </div>
  )
}
