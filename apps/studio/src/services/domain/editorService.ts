/**
 * Editor file CRUD API wrappers.
 */
import { getApiBase } from '../core/backendDetection'
import { apiFetch } from '../core/apiClient'

interface FileListResponse {
  files: string[]
  [key: string]: unknown
}

interface FileContentResponse {
  content: string
  [key: string]: unknown
}

interface FileWriteResponse {
  ok: boolean
  [key: string]: unknown
}

const base = (): string => getApiBase()

/**
 * A refused or failed editor request: the HTTP status and the server's
 * machine-readable `error_code` (e.g. `read_only_cartridge`,
 * `not_cartridge_owner`), so callers can say why in the user's language.
 */
export class EditorRequestError extends Error {
  readonly status: number
  readonly code: string | null

  constructor(message: string, status: number, code: string | null) {
    super(message)
    this.name = 'EditorRequestError'
    this.status = status
    this.code = code
  }
}

/** Build the error for a non-2xx response; a body that is not JSON (a proxy's 502 page) still yields one. */
async function requestFailure(res: Response, fallback: string): Promise<EditorRequestError> {
  let body: { error?: unknown; error_code?: unknown } = {}
  try {
    body = await res.json()
  } catch {
    // Not JSON: keep the fallback message and the status.
  }
  const message = typeof body?.error === 'string' && body.error ? body.error : fallback
  const code = typeof body?.error_code === 'string' ? body.error_code : null
  return new EditorRequestError(message, res.status, code)
}

export async function listFiles(slug: string): Promise<FileListResponse> {
  const res = await apiFetch(`${base()}/api/projects/${slug}/files`)
  if (!res.ok) throw await requestFailure(res, 'Failed to list files')
  return res.json()
}

export async function readFile(slug: string, path: string): Promise<FileContentResponse> {
  const res = await apiFetch(`${base()}/api/projects/${slug}/files/${path}`)
  if (!res.ok) throw await requestFailure(res, 'Failed to read file')
  return res.json()
}

export async function writeFile(slug: string, path: string, content: string): Promise<FileWriteResponse> {
  const res = await apiFetch(`${base()}/api/projects/${slug}/files/${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
  if (!res.ok) throw await requestFailure(res, 'Failed to write file')
  return res.json()
}

export async function createFile(slug: string, path: string, content: string = ''): Promise<FileWriteResponse> {
  const res = await apiFetch(`${base()}/api/projects/${slug}/files`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, content }),
  })
  if (!res.ok) throw await requestFailure(res, 'Failed to create file')
  return res.json()
}

export async function deleteFile(slug: string, path: string): Promise<FileWriteResponse> {
  const res = await apiFetch(`${base()}/api/projects/${slug}/files/${path}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw await requestFailure(res, 'Failed to delete file')
  return res.json()
}

export interface GraphBindingsResponse {
  bindings: Record<string, string | string[]>
}

/**
 * Set (string or list) or clear (null) the `binding` of existing manifest
 * parameters. The server only accepts this on a fork and validates the result
 * against the project's graph sources; the error it returns says why not.
 */
export async function updateGraphBindings(
  slug: string,
  bindings: Record<string, string | string[] | null>,
): Promise<GraphBindingsResponse> {
  const res = await apiFetch(`${base()}/api/projects/${slug}/manifest/bindings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bindings }),
  })
  if (!res.ok) throw new Error((await res.json()).error || 'Failed to save bindings')
  return res.json()
}
