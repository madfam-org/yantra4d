/**
 * Geometry core (WASM) — experimental browser path.
 *
 * `@madfam/geom-core` is the shared mesh-analysis library of the geometry
 * factories ("mesh in, numbers out"). This module is the Studio's only seam to
 * it: the feature flag, the lazy WASM loader, and the analysis calls. The
 * TypeScript implementations in `stl-utils.ts` and `printEstimator.ts` stay the
 * default path and the differential oracle (see `geomCore.differential.*.test.js`).
 *
 * The flag is OFF by default. Precedence, highest first (read once at page
 * load, like `?render=` in renderService.ts, so it cannot flip mid-session):
 *   1. `?geomcore=1|0` (also true/false/on/off) — per-session runtime toggle
 *   2. `VITE_GEOM_CORE_BROWSER=1|0`               — build-time pin
 *   3. off
 *
 * The WASM is loaded only when the flag is on: the package and its `.wasm`
 * live in their own lazy chunk/asset and the default bundle does not import
 * them. Failures are visible, never silent: the first failure is logged with
 * its reason, `getGeomCoreBrowserStatus()` reports it, and callers fall back to
 * the TypeScript result they would have produced with the flag off.
 */

import type { Analyzer, GeomCoreModule, GeomCoreOptions, Vec3 } from '@madfam/geom-core/wasm'

/** Release this Studio pins (apps/studio/package.json). */
export const GEOM_CORE_VERSION = '0.2.0'

/** Upper bound for module initialisation; a stuck download or compile must not hang the Studio. */
const LOAD_TIMEOUT_MS = 10_000

export function parseGeomCoreFlag(value: string | null | undefined): boolean | null {
  if (value == null) return null
  const v = value.trim().toLowerCase()
  if (v === '1' || v === 'true' || v === 'on') return true
  if (v === '0' || v === 'false' || v === 'off') return false
  return null
}

const GEOM_CORE_BROWSER_ENABLED: boolean = (() => {
  if (typeof window !== 'undefined' && window.location) {
    try {
      const fromQuery = parseGeomCoreFlag(new URLSearchParams(window.location.search).get('geomcore'))
      if (fromQuery !== null) return fromQuery
    } catch { /* malformed search string — fall through to env */ }
  }
  return parseGeomCoreFlag(import.meta.env.VITE_GEOM_CORE_BROWSER as string | undefined) ?? false
})()

export function isGeomCoreBrowserEnabled(): boolean {
  return GEOM_CORE_BROWSER_ENABLED
}

export type GeomCoreState = 'off' | 'idle' | 'loading' | 'ready' | 'failed'

export interface GeomCoreBrowserStatus {
  enabled: boolean
  state: GeomCoreState
  version: string
  /** Why the WASM path is not in use, when it was asked for and failed. */
  reason: string | null
}

let state: GeomCoreState = GEOM_CORE_BROWSER_ENABLED ? 'idle' : 'off'
let failureReason: string | null = null
let modulePromise: Promise<GeomCoreModule> | null = null

export function getGeomCoreBrowserStatus(): GeomCoreBrowserStatus {
  return { enabled: GEOM_CORE_BROWSER_ENABLED, state, version: GEOM_CORE_VERSION, reason: failureReason }
}

/** Record a failure once, loudly; later failures only update the reason. */
export function reportGeomCoreFailure(err: unknown): string {
  const reason = err instanceof Error ? err.message : String(err)
  if (state !== 'failed') {
    console.warn(`[geom-core] WASM path unavailable, using the TypeScript path: ${reason}`)
  }
  state = 'failed'
  failureReason = reason
  return reason
}

function runningUnderNode(): boolean {
  const proc = (globalThis as { process?: { versions?: { node?: string } } }).process
  return Boolean(proc?.versions?.node)
}

function withTimeout<T>(promise: Promise<T>, ms: number, what: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`${what} did not finish within ${ms} ms`)), ms)
    promise.then(
      (v) => { clearTimeout(timer); resolve(v) },
      (e) => { clearTimeout(timer); reject(e) },
    )
  })
}

/**
 * geom-core 0.2.0's default `./wasm` entry is a single-threaded ES-module
 * build (no SharedArrayBuffer, no worker pool), so it needs no cross-origin
 * isolation and loads on the Studio's pages as they are served today. The
 * threaded build is the separate `@madfam/geom-core/threaded` entry, which the
 * Studio does not use.
 */
async function instantiate(): Promise<GeomCoreModule> {
  const { default: createGeomCore } = await import('@madfam/geom-core/wasm')
  const options: GeomCoreOptions = {}
  if (!runningUnderNode()) {
    // Vite emits the package's `.wasm` (export `./wasm-binary`) as a hashed
    // asset; hand its URL to the Emscripten loader. Under Node (Vitest) the
    // loader reads the file from node_modules itself.
    const { default: wasmUrl } = await import('@madfam/geom-core/wasm-binary?url')
    options.locateFile = (path: string) => (path.endsWith('.wasm') ? wasmUrl : path)
  }
  return withTimeout(
    createGeomCore(options),
    LOAD_TIMEOUT_MS,
    `@madfam/geom-core ${GEOM_CORE_VERSION} initialisation`,
  )
}

/**
 * Load the WASM module once. Rejects with the reason when it cannot start;
 * a failed load is not retried within the session.
 */
export function loadGeomCore(): Promise<GeomCoreModule> {
  if (!modulePromise) {
    state = 'loading'
    modulePromise = instantiate().then(
      (mod) => {
        state = 'ready'
        failureReason = null
        console.info(`[geom-core] ${GEOM_CORE_VERSION} WASM active (single-threaded); mesh metrics come from geom-core`)
        return mod
      },
      (err) => { reportGeomCoreFailure(err); throw err },
    )
  }
  return modulePromise
}

export interface GeomCoreSTLMetrics {
  /** Triangles the analyzer read. */
  faceCount: number
  /** Axis-aligned bounding box in mm, straight from `getBoundingBox()`. */
  bbox: { min: [number, number, number]; max: [number, number, number] }
  /** Bounding-box extents [x, y, z] in mm (`max - min`). */
  size: [number, number, number]
  /** |signed volume| in mm³ (divergence theorem, same method as printEstimator). */
  volumeMm3: number
  /** Signed volume in mm³: negative when the closed surface is inside out. */
  signedVolumeMm3: number
  /** Volumetric centroid in mm; the origin when |volume| < 1e-9 (same rule as printEstimator). */
  centroid: Vec3
}

const xyz = (v: Vec3): [number, number, number] => [v.x, v.y, v.z]

function withAnalyzer<T>(mod: GeomCoreModule, bytes: Uint8Array, fn: (a: Analyzer) => T): T {
  const analyzer = new mod.Analyzer()
  try {
    // Returns true or throws GeomCoreSTLError ("geom-core could not read the STL: <reason>").
    analyzer.loadSTLFromBytes(bytes)
    return fn(analyzer)
  } finally {
    analyzer.delete()
  }
}

/** Analyse a binary STL with geom-core. Throws (never returns a partial result) on failure. */
export function analyzeSTLBytes(mod: GeomCoreModule, bytes: Uint8Array): GeomCoreSTLMetrics {
  return withAnalyzer(mod, bytes, (a) => {
    const box = a.getBoundingBox()
    const c = a.getCentroid()
    return {
      faceCount: a.getTriangleCount(),
      bbox: { min: xyz(box.min), max: xyz(box.max) },
      size: xyz(box.size),
      volumeMm3: a.getVolume(),
      signedVolumeMm3: a.getSignedVolume(),
      centroid: { x: c.x, y: c.y, z: c.z },
    }
  })
}

/** Structural subset of THREE.BufferGeometry that the serializer reads. */
export interface TriangleSource {
  attributes: {
    position?: {
      count: number
      getX(index: number): number
      getY(index: number): number
      getZ(index: number): number
    }
  }
  index: { count: number; getX(index: number): number } | null
}

/**
 * Serialize a (possibly indexed) triangle geometry to binary STL, the input
 * geom-core's browser binding accepts. BufferGeometry positions are float32,
 * so the round trip through STL's float32 coordinates is lossless.
 */
export function geometryToSTLBytes(geometry: TriangleSource): Uint8Array {
  const pos = geometry.attributes.position
  if (!pos) throw new Error('geometry has no position attribute')
  const index = geometry.index
  const triCount = Math.floor((index ? index.count : pos.count) / 3)
  const buffer = new ArrayBuffer(84 + triCount * 50)
  const view = new DataView(buffer)
  view.setUint32(80, triCount, true)
  let offset = 84
  for (let i = 0; i < triCount; i++) {
    offset += 12 // normal: geom-core derives its own
    for (let v = 0; v < 3; v++) {
      const vi = index ? index.getX(i * 3 + v) : i * 3 + v
      view.setFloat32(offset, pos.getX(vi), true); offset += 4
      view.setFloat32(offset, pos.getY(vi), true); offset += 4
      view.setFloat32(offset, pos.getZ(vi), true); offset += 4
    }
    offset += 2 // attribute byte count
  }
  return new Uint8Array(buffer)
}
