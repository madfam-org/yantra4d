/**
 * Git operations API wrappers.
 */
import { getApiBase } from '../core/backendDetection'
import { apiFetch } from '../core/apiClient'

interface GitStatusResponse {
  clean: boolean
  files: Array<{ path: string; status: string }>
  branch?: string
  [key: string]: unknown
}

interface GitDiffResponse {
  diff: string
  [key: string]: unknown
}

interface GitCommitResponse {
  hash: string
  message: string
  [key: string]: unknown
}

interface GitLogEntry {
  hash: string
  message: string
  author: string
  date: string
}

interface GitPushPullResponse {
  ok: boolean
  [key: string]: unknown
}

interface GitConnectRemoteResponse {
  ok: boolean
  [key: string]: unknown
}

interface GitRenderHeadPayload {
  file: string
  [key: string]: unknown
}

interface GitRenderHeadResponse {
  parts: Array<{ type: string; url: string }>
  [key: string]: unknown
}

const base = (): string => getApiBase()

export async function getStatus(slug: string): Promise<GitStatusResponse> {
  const res = await apiFetch(`${base()}/api/projects/${slug}/git/status`)
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to get git status')
  return res.json()
}

export async function getDiff(slug: string, file: string | null = null): Promise<GitDiffResponse> {
  const params = file ? `?file=${encodeURIComponent(file)}` : ''
  const res = await apiFetch(`${base()}/api/projects/${slug}/git/diff${params}`)
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to get diff')
  return res.json()
}

export async function commit(slug: string, message: string, files?: string[]): Promise<GitCommitResponse> {
  const res = await apiFetch(`${base()}/api/projects/${slug}/git/commit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, files }),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Commit failed')
  return res.json()
}

export async function push(slug: string): Promise<GitPushPullResponse> {
  const res = await apiFetch(`${base()}/api/projects/${slug}/git/push`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Push failed')
  return res.json()
}

export async function connectRemote(slug: string, remoteUrl: string): Promise<GitConnectRemoteResponse> {
  const res = await apiFetch(`${base()}/api/projects/${slug}/git/connect-remote`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ remote_url: remoteUrl }),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to connect remote')
  return res.json()
}

export async function pull(slug: string): Promise<GitPushPullResponse> {
  const res = await apiFetch(`${base()}/api/projects/${slug}/git/pull`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Pull failed')
  return res.json()
}

export async function renderHead(slug: string, payload: GitRenderHeadPayload): Promise<GitRenderHeadResponse> {
  const res = await apiFetch(`${base()}/api/projects/${slug}/git/render-head`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Render HEAD failed')
  return res.json()
}
