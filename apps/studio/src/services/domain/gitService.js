/**
 * Git operations API wrappers.
 */
import { getApiBase } from '../core/backendDetection'
import { apiFetch } from '../core/apiClient'

const base = () => getApiBase()

export async function getStatus(slug) {
  const res = await apiFetch(`${base()}/api/projects/${slug}/git/status`)
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to get git status')
  return res.json()
}

export async function getDiff(slug, file = null) {
  const params = file ? `?file=${encodeURIComponent(file)}` : ''
  const res = await apiFetch(`${base()}/api/projects/${slug}/git/diff${params}`)
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to get diff')
  return res.json()
}

export async function commit(slug, message, files) {
  const res = await apiFetch(`${base()}/api/projects/${slug}/git/commit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, files }),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Commit failed')
  return res.json()
}

export async function push(slug) {
  const res = await apiFetch(`${base()}/api/projects/${slug}/git/push`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Push failed')
  return res.json()
}

export async function connectRemote(slug, remoteUrl) {
  const res = await apiFetch(`${base()}/api/projects/${slug}/git/connect-remote`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ remote_url: remoteUrl }),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to connect remote')
  return res.json()
}

export async function pull(slug) {
  const res = await apiFetch(`${base()}/api/projects/${slug}/git/pull`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Pull failed')
  return res.json()
}
