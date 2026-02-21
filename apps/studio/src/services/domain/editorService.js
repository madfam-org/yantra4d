/**
 * Editor file CRUD API wrappers.
 */
import { getApiBase } from '../core/backendDetection'
import { apiFetch } from '../core/apiClient'

const base = () => getApiBase()

export async function listFiles(slug) {
  const res = await apiFetch(`${base()}/api/projects/${slug}/files`)
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to list files')
  return res.json()
}

export async function readFile(slug, path) {
  const res = await apiFetch(`${base()}/api/projects/${slug}/files/${path}`)
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to read file')
  return res.json()
}

export async function writeFile(slug, path, content) {
  const res = await apiFetch(`${base()}/api/projects/${slug}/files/${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to write file')
  return res.json()
}

export async function createFile(slug, path, content = '') {
  const res = await apiFetch(`${base()}/api/projects/${slug}/files`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, content }),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to create file')
  return res.json()
}

export async function deleteFile(slug, path) {
  const res = await apiFetch(`${base()}/api/projects/${slug}/files/${path}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to delete file')
  return res.json()
}
