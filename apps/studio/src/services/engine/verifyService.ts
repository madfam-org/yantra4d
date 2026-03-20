/**
 * Verification service with dual-mode support:
 * - Backend mode: uses Flask API (trimesh-based)
 * - Client mode: uses manifold-3d for in-browser mesh verification
 */

import { isBackendAvailable, getApiBase } from '../core/backendDetection'
import { parseSTL, getBoundingBox } from '../../lib/stl-utils'
import { apiFetch } from '../core/apiClient'

const API_BASE: string = getApiBase()

interface PartInput {
  type: string
  url: string
}

interface PartCheckResult {
  name: string
  passed: boolean
}

interface PartResult {
  type: string
  checks: PartCheckResult[]
}

interface VerifyResult {
  status: string
  passed: boolean
  output: string
  parts_checked: number
}

interface ManifoldModule {
  default: () => Promise<{
    Manifold: new (mesh: unknown) => {
      status(): number
      getProperties(): { volume: number; surfaceArea: number }
      delete(): void
    }
    Mesh: new (opts: { numProp: number; vertProperties: Float32Array; triVerts: Uint32Array }) => {
      delete(): void
    }
  }>
}

/**
 * Client-side verification using manifold-3d.
 */
async function verifyClient(parts: PartInput[]): Promise<VerifyResult> {
  // Dynamic import to keep bundle small if not used
  const Module = await import('manifold-3d') as unknown as ManifoldModule
  const wasm = await Module.default()
  const { Manifold, Mesh } = wasm

  const results: PartResult[] = []
  let allPassed = true
  const outputLines: string[] = []

  for (const part of parts) {
    const partResult: PartResult = { type: part.type, checks: [] }
    outputLines.push(`\n--- Part: ${part.type} ---`)

    try {
      // Fetch STL data
      const response = await fetch(part.url)
      if (!response.ok) throw new Error(`Failed to fetch STL for ${part.type}: HTTP ${response.status}`)
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
        outputLines.push(`  Volume: ${props.volume.toFixed(2)} mm\u00B3`)
        outputLines.push(`  Surface area: ${props.surfaceArea.toFixed(2)} mm\u00B2`)
        partResult.checks.push({ name: 'volume', passed: props.volume > 0 })

        manifold.delete()
        mesh.delete()
      } catch (manifoldErr) {
        outputLines.push(`  Manifold check: FAILED (${(manifoldErr as Error).message})`)
        partResult.checks.push({ name: 'watertight', passed: false })
        allPassed = false
      }
    } catch (e) {
      outputLines.push(`  ERROR: ${(e as Error).message}`)
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
async function verifyBackend(mode: string, project?: string): Promise<VerifyResult> {
  const payload: Record<string, string> = { mode }
  if (project) payload.project = project
  const res = await apiFetch(`${API_BASE}/api/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) throw new Error(`Verification failed: ${res.status}`)
  return res.json()
}

/**
 * Verify rendered parts.
 */
export async function verify(parts: PartInput[], mode: string, project?: string): Promise<VerifyResult> {
  const backend = await isBackendAvailable()
  if (backend) {
    return verifyBackend(mode, project)
  }
  return verifyClient(parts)
}
