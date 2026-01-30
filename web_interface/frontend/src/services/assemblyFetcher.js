/**
 * Fetches assembly-mode STL geometry for use in the animated grid.
 * Caches results by parameter hash to avoid redundant renders.
 */

import { STLLoader } from 'three/examples/jsm/loaders/STLLoader'
import { getApiBase } from './backendDetection'

const API_BASE = getApiBase()
const cache = new Map()
const loader = new STLLoader()

function paramHash(params) {
  const keys = ['size', 'thick', 'rod_D', 'clearance', 'fit_clear',
    'letter_depth', 'letter_size', 'rod_extension', 'rotation_clearance',
    'letter_bottom', 'letter_top']
  const obj = {}
  for (const k of keys) {
    if (params[k] !== undefined) obj[k] = params[k]
  }
  return JSON.stringify(obj)
}

/**
 * Fetch assembly STL parts and parse them into BufferGeometry objects.
 * Returns an array of { type, geometry } for assembly parts (bottom, top).
 */
export async function fetchAssemblyGeometries(params) {
  const hash = paramHash(params)
  if (cache.has(hash)) return cache.get(hash)

  const payload = { ...params, mode: 'assembly' }
  const response = await fetch(`${API_BASE}/api/render`, {
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
      const res = await fetch(fullUrl)
      if (!res.ok) throw new Error(`Failed to fetch STL: ${fullUrl}`)
      const buffer = await res.arrayBuffer()
      const geometry = loader.parse(buffer)
      geometry.computeVertexNormals()
      return { type: part.type, geometry }
    })
  )

  cache.set(hash, geometries)
  return geometries
}
