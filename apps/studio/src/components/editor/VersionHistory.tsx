import { useState, useEffect } from 'react'
import { apiFetch } from '../../services/core/apiClient'
import { useLanguage } from '../../contexts/system/LanguageProvider'

interface CommitEntry {
  hash: string
  short_hash: string
  date: string
  message: string
  author: string
}

interface VersionHistoryProps {
  projectSlug: string
  onClose: () => void
}

export default function VersionHistory({ projectSlug, onClose }: VersionHistoryProps) {
  const _t = useLanguage().t
  const [commits, setCommits] = useState<CommitEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedHash, setSelectedHash] = useState<string | null>(null)

  useEffect(() => {
    if (!projectSlug) return
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)
    setError(null)
    apiFetch(`/api/projects/${projectSlug}/git/log?limit=20`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data: { commits?: CommitEntry[] }) => {
        setCommits(data.commits || [])
        setLoading(false)
      })
      .catch((err: Error) => {
        setError(err.message)
        setLoading(false)
      })
  }, [projectSlug])

  return (
    <div className="flex flex-col h-full" data-testid="version-history">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <h3 className="text-sm font-semibold">Version History</h3>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Close history"
        >
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        )}

        {error && (
          <p className="text-xs text-destructive px-3 py-4 text-center">{error}</p>
        )}

        {!loading && !error && commits.length === 0 && (
          <p className="text-xs text-muted-foreground px-3 py-4 text-center">No commits found.</p>
        )}

        {!loading && commits.map((commit) => (
          <button
            key={commit.hash}
            type="button"
            className={`w-full text-left px-3 py-2 border-b border-border/50 hover:bg-accent transition-colors ${selectedHash === commit.hash ? 'bg-accent' : ''}`}
            onClick={() => setSelectedHash(commit.hash === selectedHash ? null : commit.hash)}
            aria-pressed={selectedHash === commit.hash}
          >
            <div className="flex items-baseline gap-2">
              <span className="text-xs font-mono text-primary shrink-0">{commit.short_hash}</span>
              <span className="text-xs text-muted-foreground truncate">{commit.date}</span>
            </div>
            <p className="text-xs mt-0.5 line-clamp-2">{commit.message}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">{commit.author}</p>
          </button>
        ))}
      </div>
    </div>
  )
}
