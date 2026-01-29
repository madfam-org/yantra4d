/**
 * Verification service with dual-mode support:
 * - Backend mode: uses Flask API (trimesh-based)
 * - Client mode: uses manifold-3d for in-browser mesh verification
 */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000'

let _backendAvailable = null

async function checkBackend() {
  if (_backendAvailable !== null) return _backendAvailable
  try {
    const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(2000) })
    _backendAvailable = res.ok
  } catch {
    _backendAvailable = false
  }
  return _backendAvailable
}

import { parseSTL, getBoundingBox } from '../lib/stl-utils'

/**
 * Client-side verification using manifold-3d.
 */
async function verifyClient(parts) {
  // Dynamic import to keep bundle small if not used
  const Module = await import('manifold-3d')
  const wasm = await Module.default()
  const { Manifold, Mesh } = wasm

  const results = []
  let allPassed = true
  const outputLines = []

  for (const part of parts) {
    const partResult = { type: part.type, checks: [] }
    outputLines.push(`\n--- Part: ${part.type} ---`)

    try {
      // Fetch STL data
      const response = await fetch(part.url)
      const buffer = await response.arrayBuffer()
      const { vertices, faces, faceCount } = parseSTL(buffer)

      outputLines.push(`  Faces: ${faceCount}`)

      // Bounding box check
      const bbox = getBoundingBox(vertices)
      outputLines.push(`  Bounding box: ${bbox.size.map(v => v.toFixed(2)).join(' x ')} mm`)
      partResult.checks.push({ name: 'geometry', passed: faceCount > 0 })

      // Manifold check using manifold-3d
      try {
        const mesh = new Mesh({
          numProp: 3,
          vertProperties: vertices,
          triVerts: faces
        })
        const manifold = new Manifold(mesh)
        const status = manifold.status()
        const isManifold = status === 0 // 0 = no error

        outputLines.push(`  Manifold: ${isManifold ? 'YES' : 'NO (non-manifold)'}`)
        partResult.checks.push({ name: 'watertight', passed: isManifold })

        if (!isManifold) allPassed = false

        // Volume check
        const props = manifold.getProperties()
        outputLines.push(`  Volume: ${props.volume.toFixed(2)} mm³`)
        outputLines.push(`  Surface area: ${props.surfaceArea.toFixed(2)} mm²`)
        partResult.checks.push({ name: 'volume', passed: props.volume > 0 })

        manifold.delete()
        mesh.delete()
      } catch (manifoldErr) {
        outputLines.push(`  Manifold check: FAILED (${manifoldErr.message})`)
        partResult.checks.push({ name: 'watertight', passed: false })
        allPassed = false
      }
    } catch (e) {
      outputLines.push(`  ERROR: ${e.message}`)
      partResult.checks.push({ name: 'load', passed: false })
      allPassed = false
    }

    results.push(partResult)
  }

  return {
    status: allPassed ? 'passed' : 'failed',
    passed: allPassed,
    output: outputLines.join('\n'),
    parts_checked: results.length
  }
}

/**
 * Backend verification.
 */
async function verifyBackend(mode) {
  const res = await fetch(`${API_BASE}/api/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode })
  })
  if (!res.ok) throw new Error(`Verification failed: ${res.status}`)
  return res.json()
}

/**
 * Verify rendered parts.
 *
 * @param {Array<{type: string, url: string}>} parts - Rendered parts with URLs
 * @param {string} mode - Current mode
 * @returns {Promise<{status: string, passed: boolean, output: string, parts_checked: number}>}
 */
export async function verify(parts, mode) {
  const backend = await checkBackend()
  if (backend) {
    return verifyBackend(mode)
  }
  return verifyClient(parts)
}
