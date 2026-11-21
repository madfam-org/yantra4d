/**
 * The public, read-only graph view's data: GET /api/projects/<slug>/graph?mode=<id>.
 *
 * Open to every visitor who may see the cartridge, signed out included; the
 * server serves only the .graph.json the manifest names for that mode.
 */
import { getApiBase } from '../core/backendDetection'
import { apiFetch } from '../core/apiClient'

export interface ModeGraph {
  mode: string
  /** The graph file's path inside the cartridge. */
  path: string
  /** `source`: the graph builds this mode. `twin`: a published twin of `script`, which still renders. */
  role: 'source' | 'twin'
  script: string | null
  content: string
}

/** A refusal with the server's machine-readable code (e.g. `not_a_graph_mode`). */
export class GraphViewError extends Error {
  status: number
  code: string | null

  constructor(message: string, status: number, code: string | null) {
    super(message)
    this.name = 'GraphViewError'
    this.status = status
    this.code = code
  }
}

export async function fetchModeGraph(slug: string, mode: string, signal?: AbortSignal): Promise<ModeGraph> {
  const url = `${getApiBase()}/api/projects/${encodeURIComponent(slug)}/graph?mode=${encodeURIComponent(mode)}`
  const res = await apiFetch(url, signal ? { signal } : {})
  if (!res.ok) {
    let message = `Graph request failed (${res.status})`
    let code: string | null = null
    try {
      const body = await res.json()
      if (typeof body?.error === 'string') message = body.error
      if (typeof body?.error_code === 'string') code = body.error_code
    } catch {
      // A non-JSON error body keeps the status message.
    }
    throw new GraphViewError(message, res.status, code)
  }
  const body = await res.json()
  if (typeof body?.content !== 'string' || typeof body?.path !== 'string') {
    throw new GraphViewError('Malformed graph response', res.status, 'malformed_response')
  }
  return {
    mode: String(body.mode ?? mode),
    path: body.path,
    role: body.role === 'twin' ? 'twin' : 'source',
    script: typeof body.script === 'string' ? body.script : null,
    content: body.content,
  }
}

/** Whether a manifest mode declares a graph the view can show (a graph scad_file or a graph_file twin). */
export function modeDeclaresGraph(mode: { scad_file?: unknown; graph_file?: unknown } | null | undefined): boolean {
  if (!mode) return false
  const isGraph = (v: unknown) => typeof v === 'string' && v.endsWith('.graph.json')
  return isGraph(mode.scad_file) || isGraph(mode.graph_file)
}
