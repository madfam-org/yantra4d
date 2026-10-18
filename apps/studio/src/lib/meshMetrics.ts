/**
 * Mesh scalars for the viewer (volume, bounding box, centroid), routed through
 * geom-core's WASM when `VITE_GEOM_CORE_BROWSER` / `?geomcore=1` is on.
 *
 * Flag off (the default): every function here is a pass-through to the
 * printEstimator implementation with the same argument — the default path is
 * unchanged, and the WASM is never imported.
 *
 * Flag on: `prefetchGeomCoreMetrics(geometry)` analyses the geometry with
 * geom-core once (async) and caches the result per geometry object; the sync
 * accessors then return the WASM numbers for that geometry. Until the WASM
 * result exists — or if the WASM cannot run — they return the TypeScript
 * numbers, and the failure is reported by geomCoreBrowser.
 */

import { computeVolumeMm3, computeBoundingBox, computeCentroid } from './printEstimator'
import {
  isGeomCoreBrowserEnabled,
  loadGeomCore,
  analyzeSTLBytes,
  geometryToSTLBytes,
  reportGeomCoreFailure,
  type TriangleSource,
} from './geomCoreBrowser'

type GeometryArg = Parameters<typeof computeVolumeMm3>[0]
type Vec3 = { x: number; y: number; z: number }
type Dims = { width: number; depth: number; height: number }

export interface GeomCoreMeshMetrics {
  volumeMm3: number
  boundingBox: Dims
  centroid: Vec3
}

const wasmMetrics = new WeakMap<object, GeomCoreMeshMetrics>()

/** WASM metrics for this geometry, or null (flag off, not yet computed, or failed). */
export function cachedGeomCoreMetrics(geometry: object | null | undefined): GeomCoreMeshMetrics | null {
  if (!geometry || !isGeomCoreBrowserEnabled()) return null
  return wasmMetrics.get(geometry) ?? null
}

export function meshVolumeMm3(geometry: GeometryArg): number {
  return cachedGeomCoreMetrics(geometry)?.volumeMm3 ?? computeVolumeMm3(geometry)
}

export function meshBoundingBox(geometry: GeometryArg): Dims {
  return cachedGeomCoreMetrics(geometry)?.boundingBox ?? computeBoundingBox(geometry)
}

export function meshCentroid(geometry: GeometryArg): Vec3 {
  return cachedGeomCoreMetrics(geometry)?.centroid ?? computeCentroid(geometry)
}

/** Analyse a geometry with geom-core without touching the cache (differential tests use this). */
export async function computeGeomCoreMetrics(geometry: TriangleSource): Promise<GeomCoreMeshMetrics> {
  const mod = await loadGeomCore()
  const m = analyzeSTLBytes(mod, geometryToSTLBytes(geometry))
  return {
    volumeMm3: m.volumeMm3,
    // Same axis mapping as computeBoundingBox: Z-up, so height is the Z extent.
    boundingBox: { width: m.size[0], depth: m.size[1], height: m.size[2] },
    centroid: m.centroid,
  }
}

/**
 * Compute and cache the WASM metrics for a geometry. Resolves true when new
 * metrics were cached (the caller should recompute its stats), false when the
 * flag is off, the metrics were already cached, or the WASM failed.
 */
export async function prefetchGeomCoreMetrics(geometry: TriangleSource | null | undefined): Promise<boolean> {
  if (!geometry || !isGeomCoreBrowserEnabled() || !geometry.attributes?.position) return false
  if (wasmMetrics.has(geometry)) return false
  try {
    wasmMetrics.set(geometry, await computeGeomCoreMetrics(geometry))
    return true
  } catch (err) {
    reportGeomCoreFailure(err)
    return false
  }
}
