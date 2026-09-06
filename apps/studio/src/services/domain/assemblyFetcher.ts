/**
 * Fetches assembly-mode STL geometry for use in the animated grid.
 * Caches results by parameter hash to avoid redundant renders.
 */

import { BufferGeometry, BufferAttribute } from 'three'
import { getApiBase } from '../core/backendDetection'
import { apiFetch } from '../core/apiClient'

interface AssemblyGeometry {
  type: string
  geometry: BufferGeometry
}

interface RenderResponsePart {
  type: string
  url: string
}

interface RenderResponse {
  parts: RenderResponsePart[]
}

interface WorkerGeometryData {
  positions: Float32Array
  normals?: Float32Array
}

interface WorkerMessage {
  id: string
  success: boolean
  geometryData: WorkerGeometryData
  error?: string
}

const API_BASE: string = getApiBase()
const cache = new Map<string, AssemblyGeometry[]>()

// Singleton worker to avoid thread explosion
let stlWorkerInstance: Worker | null = null

/**
 * Upper bound on one STL parse. A worker that dies (out of memory, a thrown
 * error inside the parser, a browser that never started it) never posts a
 * `message`, and a promise that waits only for `message` then stays pending
 * forever — which is how the animated grid sat at "preparing" with nothing
 * left to wait for. Every path below settles: message, error, messageerror,
 * abort, or this timer.
 */
export const STL_PARSE_TIMEOUT_MS = 120_000

function abortError(message = 'STL parse aborted'): Error {
  if (typeof DOMException !== 'undefined') return new DOMException(message, 'AbortError')
  const err = new Error(message)
  err.name = 'AbortError'
  return err
}

/** True when `err` is the abort we raise ourselves or the platform's own AbortError. */
export function isAbortError(err: unknown): boolean {
  return !!err && typeof err === 'object' && (err as { name?: string }).name === 'AbortError'
}

function getWorker(): Worker {
  if (!stlWorkerInstance) {
    stlWorkerInstance = new Worker(new URL('../../workers/stlWorker.js', import.meta.url), {
      type: 'module'
    })
  }
  return stlWorkerInstance
}

/** Drop the singleton so the next parse starts a fresh worker (after a crash). */
function discardWorker(worker: Worker): void {
  if (stlWorkerInstance === worker) stlWorkerInstance = null
  try { worker.terminate() } catch { /* already gone */ }
}

function paramHash(params: Record<string, unknown>, geometryKeys: string[]): string {
  const obj: Record<string, unknown> = {}
  for (const k of geometryKeys) {
    if (params[k] !== undefined) obj[k] = params[k]
  }
  return JSON.stringify(obj)
}

function parseSTLWithWorker(fullUrl: string, signal?: AbortSignal): Promise<BufferGeometry> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(abortError())

    const worker = getWorker()
    const taskId = `assembly_${Math.random().toString(36).substring(7)}`
    let settled = false

    const cleanup = () => {
      worker.removeEventListener('message', handleMessage)
      worker.removeEventListener('error', handleError)
      worker.removeEventListener('messageerror', handleMessageError)
      signal?.removeEventListener('abort', handleAbort)
      clearTimeout(timer)
    }
    const settle = (fn: () => void) => {
      if (settled) return
      settled = true
      cleanup()
      fn()
    }

    const handleMessage = (e: MessageEvent<WorkerMessage>) => {
      const { id, success, geometryData, error } = e.data
      if (id !== taskId) return

      if (!success) {
        return settle(() => reject(new Error(error)))
      }

      const geom = new BufferGeometry()
      geom.setAttribute('position', new BufferAttribute(geometryData.positions, 3))

      if (geometryData.normals) {
        geom.setAttribute('normal', new BufferAttribute(geometryData.normals, 3))
      } else {
        geom.computeVertexNormals()
      }

      geom.computeBoundingSphere()
      geom.computeBoundingBox()

      settle(() => resolve(geom))
    }
    // A worker `error` event means the worker itself threw or died: no task id
    // will ever come back, so every pending parse on it is lost. Reject this one
    // and discard the worker so the next parse gets a live one.
    const handleError = (e: ErrorEvent) => {
      settle(() => {
        discardWorker(worker)
        reject(new Error(`STL worker failed: ${e.message || 'unknown error'}`))
      })
    }
    const handleMessageError = () => {
      settle(() => reject(new Error('STL worker sent a message that could not be deserialized')))
    }
    const handleAbort = () => settle(() => reject(abortError()))
    const timer = setTimeout(() => {
      settle(() => {
        discardWorker(worker)
        reject(new Error(`STL parse timed out after ${STL_PARSE_TIMEOUT_MS / 1000}s`))
      })
    }, STL_PARSE_TIMEOUT_MS)

    worker.addEventListener('message', handleMessage)
    worker.addEventListener('error', handleError)
    worker.addEventListener('messageerror', handleMessageError)
    signal?.addEventListener('abort', handleAbort)
    worker.postMessage({ url: fullUrl, id: taskId })
  })
}

/**
 * Fetch assembly STL parts and parse them into BufferGeometry objects.
 * Returns an array of { type, geometry } for assembly parts (bottom, top).
 */
export async function fetchAssemblyGeometries(
  params: Record<string, unknown>,
  geometryKeys: string[],
  project?: string,
  options: { signal?: AbortSignal } = {}
): Promise<AssemblyGeometry[]> {
  const { signal } = options
  const hash = paramHash(params, geometryKeys) + (project ? '|' + project : '')
  if (cache.has(hash)) return cache.get(hash)!
  if (signal?.aborted) throw abortError('Assembly fetch aborted')

  // Documented /api/render contract: {mode, parameters, parts, export_format?, project?}
  // — render parameters NESTED under 'parameters'. The previous flattened form
  // ({ ...params, mode }) was silently tolerated by the server but produced a
  // different param_hash (cache key) and dropped target_material.
  const payload: Record<string, unknown> = { mode: 'assembly', parameters: params }
  if (project) payload.project = project
  const response = await apiFetch(`${API_BASE}/api/render`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })

  if (!response.ok) {
    throw new Error(`Assembly render failed (HTTP ${response.status})`)
  }

  const data: RenderResponse = await response.json()
  const timestamp = Date.now()

  const geometries = await Promise.all(
    data.parts.map(async (part) => {
      const url = part.url + '?t=' + timestamp
      const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`

      const geometry = await parseSTLWithWorker(fullUrl, signal)

      return { type: part.type, geometry }
    })
  )

  // An aborted caller must not seed the cache with work it never consumed.
  if (signal?.aborted) throw abortError('Assembly fetch aborted')
  cache.set(hash, geometries)
  return geometries
}
