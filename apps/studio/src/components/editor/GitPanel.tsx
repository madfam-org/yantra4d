import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { GitBranch, GitCommit, ArrowUp, ArrowDown, RefreshCw, Loader2, Check, Link, History } from 'lucide-react'
import { useProject } from '../../contexts/project/ProjectProvider'
import { getStatus, getDiff, commit, push, pull, connectRemote, renderHead } from '../../services/domain/gitService'
import VersionHistory from './VersionHistory'

const SUCCESS_TOAST_DURATION_MS = 2000

interface GitStatus {
  branch?: string
  clean?: boolean
  remote?: string
  ahead?: number
  behind?: number
  modified?: string[]
  added?: string[]
  deleted?: string[]
  untracked?: string[]
  [key: string]: unknown
}

interface GitPanelProps {
  slug: string
}

export default function GitPanel({ slug }: GitPanelProps) {
  const [status, setStatus] = useState<GitStatus | null>(null)
  const [diff, setDiff] = useState('')
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [commitMsg, setCommitMsg] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [remoteUrl, setRemoteUrl] = useState('')
  const [showHistory, setShowHistory] = useState(false)

  const {
    mode, params, parts, exportFormat,
    headDiffMode, setHeadDiffMode,
    setHeadParts, loadingHeadDiff, setLoadingHeadDiff
  } = useProject()

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const s = await getStatus(slug)
      setStatus(s as unknown as GitStatus)
      // Auto-select all changed files
      const st = s as unknown as GitStatus
      const allChanged = [...(st.modified || []), ...(st.added || []), ...(st.untracked || [])]
      setSelectedFiles(allChanged)
      if (allChanged.length > 0) {
        const d = await getDiff(slug)
        setDiff(d.diff || '')
      } else {
        setDiff('')
      }
    } catch (e) {
      setError((e as Error).message)
    }
    setLoading(false)
  }, [slug])

  useEffect(() => {
    let cancelled = false
    getStatus(slug)
      .then(s => {
        if (cancelled) return
        const st = s as unknown as GitStatus
        setStatus(st)
        const allChanged = [...(st.modified || []), ...(st.added || []), ...(st.untracked || [])]
        setSelectedFiles(allChanged)
        if (allChanged.length > 0) {
          getDiff(slug).then(d => { if (!cancelled) setDiff(d.diff || '') }).catch(() => { })
        }
        setLoading(false)
      })
      .catch(e => { if (!cancelled) { setError((e as Error).message); setLoading(false) } })
    return () => { cancelled = true }
  }, [slug])

  const toggleFile = (file: string) => {
    setSelectedFiles(prev =>
      prev.includes(file) ? prev.filter(f => f !== file) : [...prev, file]
    )
  }

  const handleCommit = async () => {
    if (!commitMsg.trim() || selectedFiles.length === 0) return
    setActionLoading('commit')
    setError(null)
    try {
      await commit(slug, commitMsg.trim(), selectedFiles)
      setCommitMsg('')
      setSuccess('Committed')
      setTimeout(() => setSuccess(null), SUCCESS_TOAST_DURATION_MS)
      refresh()
    } catch (e) {
      setError((e as Error).message)
    }
    setActionLoading(null)
  }

  const handlePush = async () => {
    setActionLoading('push')
    setError(null)
    try {
      await push(slug)
      setSuccess('Pushed')
      setTimeout(() => setSuccess(null), SUCCESS_TOAST_DURATION_MS)
      refresh()
    } catch (e) {
      setError((e as Error).message)
    }
    setActionLoading(null)
  }

  const handlePull = async () => {
    setActionLoading('pull')
    setError(null)
    try {
      await pull(slug)
      setSuccess('Pulled')
      setTimeout(() => setSuccess(null), SUCCESS_TOAST_DURATION_MS)
      refresh()
    } catch (e) {
      setError((e as Error).message)
    }
    setActionLoading(null)
  }

  const hasRemote = !!status?.remote

  const handleConnectRemote = async () => {
    if (!remoteUrl.trim()) return
    setActionLoading('connect')
    setError(null)
    try {
      await connectRemote(slug, remoteUrl.trim())
      setSuccess('Remote connected')
      setRemoteUrl('')
      setTimeout(() => setSuccess(null), SUCCESS_TOAST_DURATION_MS)
      refresh()
    } catch (e) {
      setError((e as Error).message)
    }
    setActionLoading(null)
  }

  const toggleHeadDiff = async () => {
    if (headDiffMode) {
      setHeadDiffMode(false)
      setHeadParts([])
      return
    }

    setLoadingHeadDiff(true)
    setError(null)
    try {
      const payload = {
        mode,
        parameters: params,
        parts: parts.map((p: { type: string }) => p.type),
        export_format: exportFormat,
        project: slug
      }
      const res = await renderHead(slug, payload as unknown as { file: string; [key: string]: unknown })
      if ((res as unknown as { status: string }).status === 'success') {
        setHeadParts(res.parts)
        setHeadDiffMode(true)
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoadingHeadDiff(false)
    }
  }

  const allChanged = status
    ? [...(status.modified || []), ...(status.added || []), ...(status.deleted || []), ...(status.untracked || [])]
    : []

  if (showHistory) {
    return (
      <div className="border-t border-border bg-card text-sm">
        <VersionHistory projectSlug={slug} onClose={() => setShowHistory(false)} />
      </div>
    )
  }

  return (
    <div className="border-t border-border bg-card text-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-border">
        <div className="flex items-center gap-2">
          <GitBranch className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs font-medium">{status?.branch || '...'}</span>
          {status && !status.clean && (
            <span className="text-xs text-yellow-600 dark:text-yellow-400">
              {allChanged.length} changed
            </span>
          )}
          {status?.ahead !== undefined && status.ahead > 0 && (
            <span className="text-xs text-blue-600 dark:text-blue-400">
              {status.ahead} ahead
            </span>
          )}
          {status?.behind !== undefined && status.behind > 0 && (
            <span className="text-xs text-orange-600 dark:text-orange-400">
              {status.behind} behind
            </span>
          )}
          {status?.clean && (
            <span className="text-xs text-green-600 dark:text-green-400 flex items-center gap-0.5">
              <Check className="h-3 w-3" /> Clean
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-8 w-8 md:h-6 md:w-6 min-h-[44px] min-w-[44px] md:min-h-0 md:min-w-0" onClick={() => setShowHistory(v => !v)} title="Version History" aria-pressed={showHistory}>
            <History className="h-3.5 w-3.5" />
            <span className="sr-only">History</span>
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8 md:h-6 md:w-6 min-h-[44px] min-w-[44px] md:min-h-0 md:min-w-0" onClick={refresh} disabled={loading} title="Refresh status">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span className="sr-only">Refresh</span>
          </Button>
          <Button
            variant="ghost" size="icon" className="h-8 w-8 md:h-6 md:w-6 min-h-[44px] min-w-[44px] md:min-h-0 md:min-w-0"
            onClick={handlePull}
            disabled={!!actionLoading || !hasRemote}
            title={hasRemote ? 'Pull' : 'Connect to GitHub first'}
          >
            {actionLoading === 'pull' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ArrowDown className="h-3.5 w-3.5" />}
            <span className="sr-only">Pull</span>
          </Button>
          <Button
            variant="ghost" size="icon" className="h-8 w-8 md:h-6 md:w-6 min-h-[44px] min-w-[44px] md:min-h-0 md:min-w-0"
            onClick={handlePush}
            disabled={!!actionLoading || !hasRemote}
            title={hasRemote ? 'Push' : 'Connect to GitHub first'}
          >
            {actionLoading === 'push' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ArrowUp className="h-3.5 w-3.5" />}
            <span className="sr-only">Push</span>
          </Button>
        </div>
      </div>

      {error && (
        <div className="px-3 py-1.5 text-xs bg-destructive/15 text-destructive">{error}</div>
      )}
      {success && (
        <div className="px-3 py-1.5 text-xs bg-green-500/15 text-green-700 dark:text-green-400">{success}</div>
      )}

      {/* Connect to GitHub (when no remote) */}
      {status && !hasRemote && (
        <div className="px-3 py-2 border-b border-border">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Link className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs font-medium">Connect to GitHub</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={remoteUrl}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRemoteUrl(e.target.value)}
              placeholder="https://github.com/user/repo.git"
              className="flex-1 px-2 py-2 text-base md:text-xs min-h-[44px] rounded border border-border bg-background focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => { if (e.key === 'Enter') handleConnectRemote() }}
            />
            <Button
              size="sm"
              className="h-9 md:h-7 text-xs min-h-[44px] md:min-h-0"
              onClick={handleConnectRemote}
              disabled={!remoteUrl.trim() || !!actionLoading}
            >
              {actionLoading === 'connect' ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Connect'}
            </Button>
          </div>
        </div>
      )}

      {/* Changed files */}
      {allChanged.length > 0 && (
        <div className="max-h-48 overflow-y-auto">
          {allChanged.map(file => (
            <label key={file} className="flex items-center gap-2 px-3 py-2 md:py-0.5 text-xs hover:bg-muted cursor-pointer min-h-[44px] md:min-h-0">
              <input
                type="checkbox"
                checked={selectedFiles.includes(file)}
                onChange={() => toggleFile(file)}
                className="rounded"
              />
              <span className="truncate">{file}</span>
              {status?.modified?.includes(file) && <span className="text-yellow-600 dark:text-yellow-400">M</span>}
              {status?.untracked?.includes(file) && <span className="text-green-600 dark:text-green-400">?</span>}
              {status?.deleted?.includes(file) && <span className="text-red-600 dark:text-red-400">D</span>}
            </label>
          ))}
        </div>
      )}

      {/* Diff preview */}
      {diff && (
        <details className="border-t border-border">
          <summary className="flex items-center justify-between px-3 py-2 md:py-1 text-xs text-muted-foreground cursor-pointer hover:text-foreground min-h-[44px] md:min-h-0">
            <span>Diff preview</span>
            <Button
              variant={headDiffMode ? "secondary" : "outline"}
              size="sm"
              className="min-h-[44px] md:h-5 md:min-h-0 px-2 text-xs md:text-[10px]"
              disabled={loadingHeadDiff}
              onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
                e.preventDefault()
                toggleHeadDiff()
              }}
            >
              {loadingHeadDiff ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
              {headDiffMode ? "3D Diff On" : "3D Diff Off"}
            </Button>
          </summary>
          <pre className="px-3 py-1 text-[11px] max-h-40 overflow-auto bg-muted/30 font-mono whitespace-pre-wrap">{diff}</pre>
        </details>
      )}

      {/* Commit form */}
      {allChanged.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-1.5 border-t border-border">
          <input
            type="text"
            value={commitMsg}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCommitMsg(e.target.value)}
            placeholder="Commit message..."
            className="flex-1 px-2 py-2 text-base md:text-xs min-h-[44px] rounded border border-border bg-background focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => { if (e.key === 'Enter') handleCommit() }}
          />
          <Button
            size="sm"
            className="h-9 md:h-7 text-xs min-h-[44px] md:min-h-0"
            onClick={handleCommit}
            disabled={!commitMsg.trim() || selectedFiles.length === 0 || !!actionLoading}
          >
            {actionLoading === 'commit' ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <GitCommit className="h-3 w-3 mr-1" />}
            Commit
          </Button>
        </div>
      )}
    </div>
  )
}
