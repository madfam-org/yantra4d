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

function paramHash(params: Record<string, unknown>, geometryKeys: string[]): string {
  const obj: Record<string, unknown> = {}
  for (const k of geometryKeys) {
    if (params[k] !== undefined) obj[k] = params[k]
  }
  return JSON.stringify(obj)
}

function parseSTLWithWorker(fullUrl: string): Promise<BufferGeometry> {
  return new Promise((resolve, reject) => {
    if (!stlWorkerInstance) {
      stlWorkerInstance = new Worker(new URL('../../workers/stlWorker.js', import.meta.url), {
        type: 'module'
      })
    }

    const taskId = `assembly_${Math.random().toString(36).substring(7)}`

    const handleMessage = (e: MessageEvent<WorkerMessage>) => {
      const { id, success, geometryData, error } = e.data
      if (id !== taskId) return

      stlWorkerInstance!.removeEventListener('message', handleMessage)

      if (!success) {
        return reject(new Error(error))
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

      resolve(geom)
    }

    stlWorkerInstance.addEventListener('message', handleMessage)
    stlWorkerInstance.postMessage({ url: fullUrl, id: taskId })
  })
}

/**
 * Fetch assembly STL parts and parse them into BufferGeometry objects.
 * Returns an array of { type, geometry } for assembly parts (bottom, top).
 */
export async function fetchAssemblyGeometries(
  params: Record<string, unknown>,
  geometryKeys: string[]
): Promise<AssemblyGeometry[]> {
  const hash = paramHash(params, geometryKeys)
  if (cache.has(hash)) return cache.get(hash)!

  const payload: Record<string, unknown> = { ...params, mode: 'assembly' }
  const response = await apiFetch(`${API_BASE}/api/render`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
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

      const geometry = await parseSTLWithWorker(fullUrl)

      return { type: part.type, geometry }
    })
  )

  cache.set(hash, geometries)
  return geometries
}
