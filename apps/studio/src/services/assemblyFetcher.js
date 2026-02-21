/**
 * Fetches assembly-mode STL geometry for use in the animated grid.
 * Caches results by parameter hash to avoid redundant renders.
 */

import { BufferGeometry, BufferAttribute } from 'three'
import { getApiBase } from './backendDetection'
import { apiFetch } from './apiClient'

const API_BASE = getApiBase()
const cache = new Map()

// Singleton worker to avoid thread explosion
let stlWorkerInstance = null

function paramHash(params, geometryKeys) {
  const obj = {}
  for (const k of geometryKeys) {
    if (params[k] !== undefined) obj[k] = params[k]
  }
  return JSON.stringify(obj)
}

function parseSTLWithWorker(fullUrl) {
  return new Promise((resolve, reject) => {
    if (!stlWorkerInstance) {
      stlWorkerInstance = new Worker(new URL('../workers/stlWorker.js', import.meta.url), {
        type: 'module'
      })
    }

    const taskId = `assembly_${Math.random().toString(36).substring(7)}`

    const handleMessage = (e) => {
      const { id, success, geometryData, error } = e.data
      if (id !== taskId) return

      stlWorkerInstance.removeEventListener('message', handleMessage)

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
export async function fetchAssemblyGeometries(params, geometryKeys) {
  const hash = paramHash(params, geometryKeys)
  if (cache.has(hash)) return cache.get(hash)

  const payload = { ...params, mode: 'assembly' }
  const response = await apiFetch(`${API_BASE}/api/render`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(`Assembly render failed (HTTP ${response.status})`)
  }

  const data = await response.json()
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
