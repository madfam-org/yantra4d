/**
 * Render service.
 *
 * A render runs in one of two PLACEMENTS:
 *   - browser: `openscad-wasm` in a Web Worker. Free for us, unmetered for the
 *              visitor. THE DEFAULT.
 *   - server:  the Flask API's native OpenSCAD/CadQuery. Costs us CPU and costs
 *              the visitor a rate-limit unit.
 *
 * The policy that chooses between them is a PURE function in `renderPlacement.ts`.
 * This file supplies its inputs (capability probe, bundle availability, backend
 * health, per-slug failure history) and executes the result.
 */

import { isBackendAvailable, getApiBase, resetDetection } from '../core/backendDetection'
import { detectPhase, isLogWorthy } from '../../lib/openscad-phases'
import { apiFetch } from '../core/apiClient'
import {
  decideRenderPlacement,
  canRenderInBrowser,
  canRenderAnyModeInBrowser,
  effectiveModeEngine,
  placementToLegacyMode,
  type Placement,
  type PlacementDecision,
} from './renderPlacement'
import {
  getCapabilityTier,
  getPlacementPreference,
  probeDeviceCapability,
} from './renderCapability'
import {
  fetchWasmBundle,
  peekBundle,
  resolveEntryPath,
  BundleUnavailableError,
  type WasmBundle,
} from './wasmBundle'
import type { RenderFailureKind } from './openscad-worker'

interface Manifest {
  modes: ModeConfig[]
  parts: PartDef[]
  engine?: string
  project?: { slug?: string; force_backend?: boolean }
  force_backend?: boolean
  /**
   * HARD server pin. Unlike `project.force_backend` — which across the commons
   * mostly encodes "WASM cannot load our BOSL2 include or our font", a gap the
   * wasm-bundle now closes — this says the cartridge genuinely cannot be
   * rendered client-side, and nothing overrides it.
   */
  render?: { server_only?: boolean; browser_max_estimate_seconds?: number }
  estimate_constants?: EstimateConstants
  grid_presets?: Record<string, unknown>
  [key: string]: unknown
}

interface ModeConfig {
  id: string
  scad_file: string
  parts: string[]
  /**
   * Per-mode kernel override. Engine is a MODE property, not a project one:
   * `gridfinity` declares `project.engine: "cadquery"` and then three modes
   * with `engine: "openscad"`, and those three can render in a browser.
   */
  engine?: string
  estimate?: {
    formula?: string
    formula_vars?: string[]
    base_units?: number
  }
}

interface PartDef {
  id: string
  render_mode: number
  [key: string]: unknown
}

interface EstimateConstants {
  base_time: number
  per_unit: number
  per_part: number
  wasm_multiplier?: number
  warning_threshold_seconds?: number
  /** Ceiling on a single browser render, in seconds. Defaults to 120. */
  wasm_timeout_seconds?: number
}

interface ProgressEvent {
  percent?: number
  phase?: string
  part?: string
  log?: string
}

type OnProgress = (event: ProgressEvent) => void

interface RenderPart {
  type: string
  url?: string
  blob?: Blob
}

interface RenderOptions {
  onProgress?: OnProgress
  abortSignal?: AbortSignal
  project?: string
  ignoreCache?: boolean
  exportFormat?: string
  /**
   * The render's cancellable identity, as the stream publishes it. Called once
   * when the stream opens and again as each part is queued, so a caller can
   * hold a target for a render it may need to abandon later — see
   * `hooks/render/useRender.ts`. Never called on the WASM path: a browser
   * render has nothing server-side to cancel.
   */
  onJob?: (target: RenderCancelTarget) => void
}

const API_BASE = getApiBase()

/**
 * Placement decided per cartridge, not per module.
 *
 * The old `_hardwareMode` was a single module-global: the first cartridge to
 * render pinned the path for every cartridge afterwards, so opening one
 * CadQuery project sent every subsequent OpenSCAD project to the server for the
 * rest of the session. Placement is a property of (device, cartridge), so it is
 * keyed by slug.
 */
const _placementBySlug = new Map<string, Placement>()
const _decisionBySlug = new Map<string, PlacementDecision>()
/** Why a browser render failed for a slug this session; blocks a retry loop. */
const _lastBrowserFailure = new Map<string, RenderFailureKind>()
/** Which slug's bundle the live worker currently has mounted. */
let _workerSlug: string | null = null
let _worker: Worker | null = null
let _initPromise: Promise<void> | null = null
//: Wall-clock seconds of the last WASM render, compile INCLUDED. This is the
//: quantity `estimateRenderTime` claims to predict, kept so the prediction can be
//: checked against the outcome instead of being taken on faith. Read it with
//: `getLastObservedRenderSeconds()`; null until a render has completed.
let _lastObservedRenderSeconds: number | null = null
//: Cancellation identity of the backend render currently in flight, learned from
//: the stream's `job` events. `POST /api/render-cancel` acts only on the ids it
//: is given, so without this a cancel has no target — and the endpoint no longer
//: has a cancel-everything default to fall back on. Null whenever no backend
//: render is running (a browser/WASM render never sets it).
let _activeRender: { requestId: string | null, jobIds: string[] } | null = null

/**
 * Whether this device could run a browser render at all.
 *
 * Replaces the old `hardwareConcurrency >= 4 && deviceMemory >= 4` one-liner,
 * which invented a memory figure for every Firefox and Safari visitor and never
 * measured anything. See `renderCapability.ts` for what it does instead.
 */
function isBrowserRenderPossible(): boolean {
  return getCapabilityTier() !== 'incapable'
}

/**
 * The only two values the render-mode override accepts. Anything else is junk
 * and is IGNORED rather than coerced: a typo'd `?render=wsam` must fall through
 * to normal detection, not silently pin a path the operator did not ask for.
 */
function parseRenderMode(value: string | null | undefined): 'backend' | 'wasm' | null {
  if (value === 'backend' || value === 'wasm') return value
  return null
}

/**
 * Explicit render-mode override, resolved ONCE at module load.
 *
 * Read once, not per render, so the answer cannot change underneath an
 * in-flight session. The studio rewrites its own URL as the user picks a
 * preset/mode (routes are `/project/:slug/:preset/:mode`), and those rewrites
 * do not carry the query string; re-reading per render would let a pinned path
 * silently evaporate on the first such rewrite — exactly when a user on a
 * support-issued link starts clicking around. Page load is also the only moment
 * at which the operator's intent (the link they opened) is unambiguous.
 *
 * Precedence, highest first:
 *   1. `?render=backend` | `?render=wasm`  — per-session, what support hands a user
 *   2. `VITE_RENDER_MODE=backend|wasm`     — build-time pin for a whole deployment
 *   3. null                                — defer to `decideRenderPlacement`
 *
 * The override sits at rule 5 of the placement table: below the four facts
 * that make a browser render impossible (engine, `render.server_only`, an
 * unsupported bundle, an export format the kernel cannot write) and above
 * everything a heuristic could say.
 */
const RENDER_MODE_OVERRIDE: 'backend' | 'wasm' | null = (() => {
  let fromQuery: 'backend' | 'wasm' | null = null
  if (typeof window !== 'undefined' && window.location) {
    try {
      fromQuery = parseRenderMode(new URLSearchParams(window.location.search).get('render'))
    } catch { /* malformed search string — fall through to env */ }
  }
  if (fromQuery) return fromQuery
  return parseRenderMode(import.meta.env.VITE_RENDER_MODE as string | undefined)
})()

/**
 * The explicit override, or null when detection should decide.
 * Exported for diagnostics and tests.
 */
export function getRenderModeOverride(): 'backend' | 'wasm' | null {
  return RENDER_MODE_OVERRIDE
}

/** The cartridge's slug, from wherever the manifest happens to carry it. */
function manifestSlug(manifest: Manifest | null, project?: string): string {
  return project || (manifest?.project?.slug as string | undefined) || '__default__'
}

/**
 * Resolve where one render runs.
 *
 * Gathers the inputs — capability tier, user preference, override, bundle
 * state, backend health, this slug's failure history — and hands them to the
 * pure `decideRenderPlacement`. The policy itself lives there; this function
 * only fetches facts.
 *
 * WHAT CHANGED. The old `detectMode()` contained the line
 *
 *     if (API_BASE) return 'backend'
 *
 * which unconditionally pinned every render to the server whenever
 * `VITE_API_BASE` was set — and production always sets it. Every heuristic
 * below that line (the complexity breaker, the hardware check, `force_backend`)
 * was therefore dead code in production, and every visitor's render was billed
 * to us and rate-limited to them even when their laptop could have done it for
 * free. That line is gone.
 */
async function resolvePlacement(
  manifest: Manifest | null,
  mode: string,
  params: Record<string, unknown>,
  project?: string,
  exportFormat?: string,
): Promise<PlacementDecision> {
  const slug = manifestSlug(manifest, project)
  // Engine is resolved PER MODE. Reading `manifest.engine` alone would send
  // every mode of a dual-engine cartridge to the server, including the ones the
  // browser can render perfectly well.
  const engine = effectiveModeEngine(manifest, mode)
  const tier = getCapabilityTier()

  // Backend health is only consulted to learn whether a SERVER placement is
  // even possible. It never decides the browser's case.
  let backendAvailable = true
  if (canRenderInBrowser(engine)) {
    try {
      backendAvailable = await isBackendAvailable()
    } catch {
      backendAvailable = false
    }
  }

  const cachedBundle = peekBundle(slug)
  const decision = decideRenderPlacement({
    engine,
    exportFormat,
    override: RENDER_MODE_OVERRIDE,
    userPreference: getPlacementPreference(),
    capabilityTier: tier,
    bundle: cachedBundle
      ? {
          available: true,
          unsupported: cachedBundle.unsupported ?? [],
          unresolved: cachedBundle.unresolved ?? [],
        }
      : null,
    serverOnly: manifest?.render?.server_only === true,
    forceBackendHint: Boolean(manifest?.project?.force_backend || manifest?.force_backend),
    estimateSeconds: manifest && mode ? estimateRenderTime(mode, params, manifest, 'browser') : null,
    browserMaxEstimateSeconds: manifest?.render?.browser_max_estimate_seconds ?? null,
    backendAvailable,
    lastBrowserFailure: _lastBrowserFailure.get(slug) ?? null,
  })

  _placementBySlug.set(slug, decision.placement)
  _decisionBySlug.set(slug, decision)
  return decision
}

/**
 * Whether this cartridge supports client-side WASM rendering.
 *
 * With a `modeId`, answers for that mode. Without one, answers "could ANY mode
 * run in the browser?" — which is what a surface with no single mode in scope
 * (the rate-limit banner's "browser rendering is still available") actually
 * means. A dual-engine cartridge like `gridfinity` answers yes to the second
 * question even though its project engine is CadQuery.
 */
export function canRunWasm(manifest: Manifest | null, modeId?: string | null): boolean {
  if (modeId) return canRenderInBrowser(effectiveModeEngine(manifest, modeId))
  return canRenderAnyModeInBrowser(manifest)
}

/**
 * The placement decision most recently taken for a slug, for UI and diagnostics.
 * Null until this slug has rendered (or been asked about) at least once.
 */
export function getPlacementDecision(slug: string): PlacementDecision | null {
  return _decisionBySlug.get(slug) ?? null
}

/**
 * Decide a placement WITHOUT touching the network, for UI that needs an answer
 * synchronously. Uses the last known backend health rather than probing, so it
 * can differ from the render's own decision during an outage — the badge
 * catches up on the next render.
 *
 * `exportFormat` is part of the question, not a detail of the render: a format
 * the browser kernel cannot emit is a HARD server placement (rule 4), so a
 * badge that ignored it would read "Browser" for a render that is about to be
 * metered on the server.
 */
export function previewPlacement(
  // Loose on purpose. `ManifestProvider` exports its own `Manifest` interface
  // for the same JSON document, and the two are structurally incompatible in
  // TypeScript's eyes only because that one carries an index signature (so
  // `mode.scad_file` types as `unknown`). Widening here keeps the one cast in
  // this module, where the equivalence is documented, instead of pushing an
  // `as unknown as` into every UI caller.
  manifestInput: Manifest | Record<string, unknown> | null,
  mode: string,
  params: Record<string, unknown>,
  project?: string,
  exportFormat?: string,
): PlacementDecision {
  const manifest = manifestInput as Manifest | null
  const slug = manifestSlug(manifest, project)
  const cachedBundle = peekBundle(slug)
  return decideRenderPlacement({
    engine: effectiveModeEngine(manifest, mode),
    exportFormat,
    override: RENDER_MODE_OVERRIDE,
    userPreference: getPlacementPreference(),
    capabilityTier: getCapabilityTier(),
    bundle: cachedBundle
      ? {
          available: true,
          unsupported: cachedBundle.unsupported ?? [],
          unresolved: cachedBundle.unresolved ?? [],
        }
      : null,
    serverOnly: manifest?.render?.server_only === true,
    forceBackendHint: Boolean(manifest?.project?.force_backend || manifest?.force_backend),
    estimateSeconds: manifest && mode ? estimateRenderTime(mode, params, manifest, 'browser') : null,
    browserMaxEstimateSeconds: manifest?.render?.browser_max_estimate_seconds ?? null,
    backendAvailable: true,
    lastBrowserFailure: _lastBrowserFailure.get(slug) ?? null,
  })
}

/**
 * Kick off the capability micro-benchmark in the render worker.
 *
 * Runs once per device per `CAPABILITY_VERSION` per 7 days; concurrent callers
 * share one probe. Deliberately fire-and-forget: a page that never renders
 * should not pay for a WASM instantiation, and a page that does render gets a
 * static-signal answer immediately and the measured one shortly after.
 */
export function ensureCapabilityProbe(): Promise<unknown> {
  return probeDeviceCapability(runWorkerBenchmark).catch(() => { /* never fatal */ })
}

/** One-shot worker whose only job is to time an instantiate + tiny render. */
function runWorkerBenchmark(): Promise<number> {
  return new Promise<number>((resolve, reject) => {
    let worker: Worker
    try {
      worker = new Worker(new URL('./openscad-worker.js', import.meta.url), { type: 'module' })
    } catch (e) {
      reject(e as Error)
      return
    }
    // A machine that cannot finish the reference render inside this window is
    // beyond `incapable` anyway; the ceiling only stops the promise hanging.
    const timer = setTimeout(() => {
      worker.terminate()
      reject(new Error('capability benchmark timed out'))
    }, 30_000)

    worker.addEventListener('message', (e: MessageEvent) => {
      if (e.data?.type === 'benchmark-done') {
        clearTimeout(timer)
        worker.terminate()
        resolve(e.data.ms as number)
      } else if (e.data?.type === 'error' || e.data?.type === 'init-error') {
        clearTimeout(timer)
        worker.terminate()
        reject(new Error(e.data.message || e.data.error || 'benchmark failed'))
      }
    })
    worker.addEventListener('error', (e: Event) => {
      clearTimeout(timer)
      worker.terminate()
      reject(new Error((e as ErrorEvent).message || 'benchmark worker error'))
    })
    worker.postMessage({ type: 'benchmark' })
  })
}

/**
 * Check if an error is a network-level failure (not a backend render error).
 */
function isNetworkError(err: unknown): boolean {
  if (err instanceof TypeError && err.message === 'Failed to fetch') return true
  if (err instanceof DOMException && err.name === 'AbortError') return false // user cancel
  if (err instanceof Error && err.message.includes('net::ERR_')) return true
  return false
}

/**
 * Check if an error is an HTTP 429 rate limit response.
 */
function isRateLimitError(err: unknown): boolean {
  return err instanceof Error && err.message.includes('HTTP 429')
}

/**
 * Check if backend rendering failed because the render worker plane is unavailable.
 */
function isRenderWorkerUnavailableError(err: unknown): boolean {
  if (!(err instanceof Error)) return false
  return err.message.includes('Render worker unavailable or not healthy')
    || err.message.includes('render_worker_unavailable')
}

/**
 * A browser render that failed in a way the server could plausibly survive.
 *
 * Carries the worker's failure `kind` so `renderParts()` can tell an
 * environment failure (retry on the server) from a SCAD error (do not — the
 * server compiles the same source and produces the same message, for the price
 * of one rate-limit unit).
 */
export class BrowserRenderError extends Error {
  readonly kind: RenderFailureKind
  constructor(message: string, kind: RenderFailureKind) {
    super(message)
    this.name = 'BrowserRenderError'
    this.kind = kind
  }
}

/** Failure kinds worth re-attempting on the server. */
const SERVER_RETRYABLE_KINDS: ReadonlySet<RenderFailureKind> = new Set([
  'init-error',
  'oom',
  'timeout',
])

/** Default ceiling on one browser render. `estimate_constants` may override. */
const DEFAULT_WASM_TIMEOUT_SECONDS = 120

function wasmTimeoutMs(manifest: Manifest | null): number {
  const configured = manifest?.estimate_constants?.wasm_timeout_seconds
  const seconds = typeof configured === 'number' && Number.isFinite(configured) && configured > 0
    ? configured
    : DEFAULT_WASM_TIMEOUT_SECONDS
  return seconds * 1000
}

/** Tear the worker down and forget what it had mounted. */
function disposeWorker(): void {
  if (_worker) {
    _worker.terminate()
    _worker = null
  }
  _initPromise = null
  _workerSlug = null
}

/**
 * Initialize the WASM worker for a slug: fetch the render bundle and mount it.
 *
 * The bundle — not `/scad/<file>` — is the browser's source of truth. It
 * carries the entry files, every transitively included library file, and the
 * cartridge's fonts, so `include <../../libs/BOSL2/std.scad>` resolves and
 * `text()` renders. See `wasmBundle.ts` for why the old path could not.
 */
function initWorker(manifest: Manifest | null, slug: string): Promise<void> {
  // A worker holding a different cartridge's bundle is the wrong worker.
  if (_initPromise && _workerSlug === slug) return _initPromise
  if (_workerSlug !== slug) disposeWorker()

  _workerSlug = slug
  _initPromise = (async () => {
    const bundle: WasmBundle = await fetchWasmBundle(slug, { manifest: manifest ?? undefined })

    await new Promise<void>((resolve, reject) => {
      _worker = new Worker(
        new URL('./openscad-worker.js', import.meta.url),
        { type: 'module' },
      )

      const handler = (e: MessageEvent) => {
        if (e.data.type === 'init-done') {
          _worker!.removeEventListener('message', handler)
          resolve()
        } else if (e.data.type === 'init-error') {
          _worker!.removeEventListener('message', handler)
          reject(new BrowserRenderError(e.data.error, e.data.kind ?? 'init-error'))
        }
      }
      _worker.addEventListener('message', handler)
      _worker.postMessage({ type: 'init', bundle })
    })
  })()

  // A failed init must not be cached as the answer for every later render.
  _initPromise.catch(() => { disposeWorker() })

  return _initPromise
}

interface SSEData {
  progress?: number
  event?: string
  part?: string
  index?: number
  total?: number
  line?: string
  message?: string
  error?: string
  reason?: string
  parts?: RenderPart[]
  request_id?: string
  job_ids?: string[]
}

/**
 * Parse complete SSE data lines into individual JSON data objects while
 * preserving any incomplete trailing line for the next network chunk.
 *
 * The backend emits one JSON object per `data:` line. Network chunks can split
 * those lines arbitrarily, so parsing must happen only after a newline arrives.
 */
function parseSSEBuffer(buffer: string): { events: SSEData[], remainder: string } {
  const normalized = buffer.replace(/\r\n/g, '\n')
  const lines = normalized.split('\n')
  const remainder = normalized.endsWith('\n') ? '' : (lines.pop() ?? '')
  const results: SSEData[] = []
  for (const line of lines) {
    if (!line.startsWith('data:')) continue

    const data = line.slice(5).trimStart()
    if (!data) continue

    try {
      results.push(JSON.parse(data))
    } catch (e) {
      console.warn('Malformed SSE data:', e)
    }
  }
  return { events: results, remainder }
}

/**
 * Render parts via WASM worker.
 */
async function renderWasm(
  mode: string,
  params: Record<string, unknown>,
  manifest: Manifest,
  onProgress?: OnProgress,
  abortSignal?: AbortSignal,
  project?: string
): Promise<RenderPart[]> {
  const slug = manifestSlug(manifest, project)
  await initWorker(manifest, slug)

  const modeConfig = manifest.modes.find(m => m.id === mode)
  if (!modeConfig) throw new Error(`Unknown mode: ${mode}`)

  const bundle = peekBundle(slug)
  const entryPath = bundle
    ? resolveEntryPath(bundle, modeConfig.scad_file)
    : `/projects/${slug}/${modeConfig.scad_file}`
  const timeoutMs = wasmTimeoutMs(manifest)

  const parts: RenderPart[] = []
  const partTimings: { part: string; seconds: number }[] = []
  const totalParts = modeConfig.parts.length

  for (let i = 0; i < totalParts; i++) {
    if (abortSignal?.aborted) throw new DOMException('Aborted', 'AbortError')
    const partId = modeConfig.parts[i]
    const partDef = manifest.parts.find(p => p.id === partId)
    if (!partDef) {
      console.warn(`Part definition not found for: ${partId}`)
      continue
    }

    const basePercent = Math.round((i / totalParts) * 100)
    // WALL-CLOCK PER PART, spanning compile AND render.
    //
    // The engine already logs a "Total rendering time" line, but that EXCLUDES
    // the OpenSCAD/WASM compile — which is the dominant cost the operator
    // actually waits through. Calibrating estimate_constants against the engine's
    // number alone therefore fits the small half of the problem: measured 2026-08-08,
    // a 3x3 reported 0.196 s of "rendering" while the visible wait was seconds of
    // "Compilando...". Timing the await is the only place both are in scope.
    const partStart = performance.now()
    onProgress?.({
      percent: basePercent,
      phase: 'compiling',
      part: partId,
      log: `[${partId}] Starting... (${i + 1}/${totalParts})`
    })

    const stlData = await new Promise<ArrayBuffer>((resolve, reject) => {
      // THE TIMEOUT LIVES HERE, not in the worker.
      //
      // `callMain()` is a synchronous call into WASM: while it runs, the
      // worker's event loop is blocked and no timer it armed could fire. Only
      // `terminate()` from this thread can stop a runaway render — which is
      // also why the worker is discarded rather than reused afterwards.
      let settled = false
      const timer = setTimeout(() => {
        if (settled) return
        settled = true
        disposeWorker()
        reject(new BrowserRenderError(
          `Browser render exceeded ${Math.round(timeoutMs / 1000)}s`,
          'timeout',
        ))
      }, timeoutMs)

      const finish = (fn: () => void) => {
        if (settled) return
        settled = true
        clearTimeout(timer)
        fn()
      }

      const handler = (e: MessageEvent) => {
        const msg = e.data
        if (msg.type === 'result') {
          _worker?.removeEventListener('message', handler)
          finish(() => resolve(msg.stl))
        } else if (msg.type === 'error') {
          _worker?.removeEventListener('message', handler)
          finish(() => reject(new BrowserRenderError(msg.message, msg.kind ?? 'init-error')))
        } else if (msg.type === 'progress') {
          const partPercent = basePercent + Math.round((1 / totalParts) * (msg.percent || 50))
          onProgress?.({
            percent: partPercent,
            phase: msg.phase,
            part: partId,
            log: msg.line
          })
        }
      }
      if (abortSignal) {
        const onAbort = () => {
          _worker?.removeEventListener('message', handler)
          disposeWorker()
          finish(() => reject(new DOMException('Aborted', 'AbortError')))
        }
        abortSignal.addEventListener('abort', onAbort, { once: true })
      }
      _worker!.addEventListener('message', handler)
      _worker!.postMessage({
        type: 'render',
        entryPath,
        params: { ...params, mode },
        renderMode: partDef.render_mode
      })
    })

    const blob = new Blob([stlData], { type: 'application/sla' })
    const url = URL.createObjectURL(blob)
    parts.push({ type: partId, blob, url })

    const partElapsed = (performance.now() - partStart) / 1000
    partTimings.push({ part: partId, seconds: partElapsed })
    onProgress?.({
      percent: Math.round(((i + 1) / totalParts) * 100),
      phase: 'done',
      part: partId,
      log: `[${partId}] Done (${Math.round(((i + 1) / totalParts) * 100)}%) in ${partElapsed.toFixed(2)}s`
    })
  }

  // The line the estimator should be fitted against. `estimateRenderTime` predicts
  // exactly this quantity, so printing them together is what makes a bad
  // calibration visible instead of silent — the shipped constants were 1,714x high
  // and nothing in the UI ever compared the two.
  const observedTotal = partTimings.reduce((a, p) => a + p.seconds, 0)
  _lastObservedRenderSeconds = observedTotal
  onProgress?.({
    log: `[render] observed ${observedTotal.toFixed(2)}s wall-clock across ${partTimings.length} part(s)`
  })

  disposeWorker()

  return parts
}

/**
 * Render parts via backend SSE stream.
 */
async function renderBackend(
  mode: string,
  params: Record<string, unknown>,
  manifest: Manifest | null,
  onProgress?: OnProgress,
  abortSignal?: AbortSignal,
  project?: string,
  ignoreCache?: boolean,
  exportFormat?: string,
  onJob?: (target: RenderCancelTarget) => void
): Promise<RenderPart[]> {
  // Documented /api/render-stream contract:
  // {mode, parameters, parts, export_format?, project?} — parameters NESTED.
  // The previous flattened form ({ ...params, mode }) was silently tolerated by
  // the server but produced a different param_hash (cache key) than the nested
  // form and dropped target_material.
  const payload: Record<string, unknown> = { mode, parameters: params }
  if (project) payload.project = project
  if (ignoreCache) payload.ignore_cache = true

  if (exportFormat) {
    payload.export_format = exportFormat
  } else if (manifest && !canRenderInBrowser(effectiveModeEngine(manifest, mode))) {
    // The server-side kernels emit GLB for the viewer; OpenSCAD emits STL.
    // Resolved per MODE so a dual-engine cartridge's OpenSCAD modes are not
    // asked for GLB just because the project engine is CadQuery.
    payload.export_format = 'glb'
  }

  const response = await apiFetch(`${API_BASE}/api/render-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: abortSignal
  })

  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(`Render request failed (HTTP ${response.status}): ${text}`)
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let finalParts: RenderPart[] = []
  let streamFailure: string | null = null
  let sseBuffer = ''
  // This stream's own identity object, so the cleanup below can tell whether
  // `_activeRender` is still ours before clearing it.
  let myIdentity: { requestId: string | null, jobIds: string[] } | null = null

  const processEvent = (data: SSEData) => {
    if (data.progress !== undefined) {
      onProgress?.({ percent: data.progress })
    }

    if (data.event === 'job') {
      // The server re-sends this as each part is queued, carrying every id
      // issued so far, so the last one wins rather than accumulating here.
      myIdentity = {
        requestId: data.request_id ?? null,
        jobIds: data.job_ids ?? []
      }
      _activeRender = myIdentity
      const target = getActiveRenderTarget()
      if (target) onJob?.(target)
    } else if (data.event === 'part_start') {
      onProgress?.({
        part: data.part,
        log: `[${data.part}] Starting... (${data.index! + 1}/${data.total})`
      })
    } else if (data.event === 'output') {
      const line = data.line!
      const phase = detectPhase(line)
      if (phase) onProgress?.({ phase })
      if (isLogWorthy(line)) {
        onProgress?.({ log: `  ${line}` })
      }
    } else if (data.event === 'part_done') {
      // `data.progress` is optional on the wire — a backend that omits it used to
      // render literally as "[cubies] Done (undefined%)" in the operator console,
      // right underneath the WASM path's correct "[cubies] Done (14%)". Two lines
      // per part, one of them nonsense. Fall back to the part index instead of
      // interpolating undefined; drop the percentage entirely if neither is known,
      // because a missing number should read as missing, not as a value.
      const pct = typeof data.progress === 'number' && Number.isFinite(data.progress)
        ? `${Math.round(data.progress)}%`
        : null
      onProgress?.({
        part: data.part,
        log: pct ? `[${data.part}] Done (${pct})` : `[${data.part}] Done`
      })
    } else if (data.event === 'complete') {
      finalParts = data.parts || []
      if (data.error) {
        streamFailure = data.error
      }
    } else if (data.event === 'error') {
      streamFailure = data.error || data.message || 'Render failed'
      onProgress?.({ log: `[ERROR] ${data.part}: ${streamFailure}` })
    } else if (data.event === 'cancelled') {
      streamFailure = data.message || data.reason || 'Render cancelled'
      onProgress?.({ log: `[CANCELLED] ${data.part}: ${streamFailure}` })
    }
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      sseBuffer += decoder.decode(value, { stream: true })
      const parsed = parseSSEBuffer(sseBuffer)
      sseBuffer = parsed.remainder

      for (const data of parsed.events) processEvent(data)
    }

    sseBuffer += decoder.decode()
    if (sseBuffer.trim()) {
      const parsed = parseSSEBuffer(`${sseBuffer}\n\n`)
      for (const data of parsed.events) processEvent(data)
    }
  } finally {
    // The stream is over either way: these jobs are done, and holding their ids
    // would let a later cancel fire at a finished render. Clear only our own —
    // a render that started while this one was finishing owns the slot now.
    if (_activeRender === myIdentity) _activeRender = null
  }

  if (finalParts.length === 0) {
    if (streamFailure) {
      throw new Error(streamFailure)
    }
    throw new Error('Render stream completed without producing any parts')
  }

  const timestamp = Date.now()
  return finalParts.map(p => {
    // The backend returns:
    //   url        – the file in the requested export_format (e.g. .stl)
    //   viewer_url – a GLB conversion of the above (only for stl renders)
    //
    // The 3D viewer infers GLB vs STL from the URL extension, so we use
    // viewer_url as the primary `url` when available (faster viewer load).
    // The original format URL is stored as `download_url` for the download handler.
    const downloadUrl = p.url
    const viewerUrl = (p as { viewer_url?: string }).viewer_url
    const primaryUrl = viewerUrl ?? p.url
    return {
      ...p,
      url: primaryUrl + '?t=' + timestamp,
      download_url: downloadUrl + '?t=' + timestamp,
    }
  })
}

/**
 * Main entry point: render parts for the given mode and parameters.
 *
 * Falls back in BOTH directions, for different reasons:
 *
 *   server -> browser  when the server cannot take the work (network down,
 *                      429 rate limit, render worker unhealthy). Free capacity
 *                      the visitor already owns beats an error page.
 *   browser -> server  when the browser's environment failed (module would not
 *                      init, tab ran out of memory, render blew the timeout).
 *                      NOT on a SCAD error: the server compiles the identical
 *                      source and would fail identically, for the price of one
 *                      rate-limit unit.
 */
export async function renderParts(
  mode: string,
  params: Record<string, unknown>,
  manifest: Manifest,
  { onProgress, abortSignal, project, ignoreCache, exportFormat, onJob }: RenderOptions = {}
): Promise<RenderPart[]> {
  const slug = manifestSlug(manifest, project)
  const decision = await resolvePlacement(manifest, mode, params, project, exportFormat)

  if (decision.placement === 'server') {
    try {
      return await renderBackend(mode, params, manifest, onProgress, abortSignal, project, ignoreCache, exportFormat, onJob)
    } catch (err) {
      // `?render=backend` is a deliberate "keep me off WASM" instruction —
      // usually because WASM is exactly what broke for this user. Falling back
      // to it here would quietly undo the override at the one moment it matters.
      const canFallbackToBrowser = (
        !decision.hard
        && RENDER_MODE_OVERRIDE !== 'backend'
        && getPlacementPreference() !== 'server'
        && canRenderInBrowser(effectiveModeEngine(manifest, mode))
        && isBrowserRenderPossible()
        && !_lastBrowserFailure.has(slug)
      )
      const shouldFallback = (
        isNetworkError(err)
        || isRateLimitError(err)
        || isRenderWorkerUnavailableError(err)
      )
      if (canFallbackToBrowser && shouldFallback) {
        const isRL = isRateLimitError(err)
        const isWorkerUnavailable = isRenderWorkerUnavailableError(err)
        const reason = isRL ? 'rate limited' : isWorkerUnavailable ? 'worker unavailable' : 'network'
        console.warn(`[Fallback] Server render failed (${reason}), retrying in the browser:`, (err as Error).message)
        if (!isRL) resetDetection() // clear cached availability so next render re-checks
        _placementBySlug.set(slug, 'browser')
        const fallbackLog = isRL
          ? '[FALLBACK] Server limit reached, rendering in your browser...'
          : isWorkerUnavailable
            ? '[FALLBACK] Server render worker unavailable, rendering in your browser...'
            : '[FALLBACK] Server unavailable, rendering in your browser...'
        onProgress?.({ log: fallbackLog })
        return renderWasm(mode, params, manifest, onProgress, abortSignal, project)
      }
      // A hard server pin plus an exhausted quota is a dead end; say so plainly
      // rather than letting a cryptic WASM failure stand in for it.
      if (decision.hard && isRateLimitError(err)) {
        onProgress?.({ log: '[ERROR] Server render limit reached. This project requires server rendering — upgrade your plan or wait for the limit to reset.' })
      }
      if (decision.hard && isRenderWorkerUnavailableError(err)) {
        onProgress?.({ log: '[ERROR] Server render worker is unavailable. This project requires server rendering — retry after the render service recovers.' })
      }
      throw err // re-throw non-recoverable errors
    }
  }

  try {
    return await renderWasm(mode, params, manifest, onProgress, abortSignal, project)
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err

    const kind = browserFailureKind(err)
    if (!kind) throw err

    // Remember it: rule 8 of the placement table sends this slug straight to the
    // server for the rest of the session rather than re-running a failure.
    _lastBrowserFailure.set(slug, kind)
    _placementBySlug.set(slug, 'server')

    if (!SERVER_RETRYABLE_KINDS.has(kind)) {
      // A SCAD error. The server would reject the same source identically.
      onProgress?.({ log: `[ERROR] Browser render failed (${kind}). The model itself was rejected — the server would report the same error.` })
      throw err
    }
    if (RENDER_MODE_OVERRIDE === 'wasm' || getPlacementPreference() === 'browser') {
      // The visitor pinned the browser. Report the failure instead of silently
      // spending their server quota against their stated choice.
      onProgress?.({ log: `[ERROR] Browser render failed (${kind}) and browser rendering is pinned.` })
      throw err
    }
    if (!canRenderInBrowser(effectiveModeEngine(manifest, mode))) throw err

    console.warn(`[Fallback] Browser render failed (${kind}), retrying on the server:`, (err as Error).message)
    onProgress?.({ log: `[FALLBACK] Browser render failed (${kind}), rendering on our server...` })
    return renderBackend(mode, params, manifest, onProgress, abortSignal, project, ignoreCache, exportFormat)
  }
}

/**
 * Classify a browser render failure, or null when it is not one.
 *
 * A `BundleUnavailableError` is an init failure by another name: the browser
 * never got the cartridge's files, so it could not have rendered it.
 */
function browserFailureKind(err: unknown): RenderFailureKind | null {
  if (err instanceof BrowserRenderError) return err.kind
  if (err instanceof BundleUnavailableError) {
    // A locked private project is an authorization problem, not a capability
    // one. Retrying it on the server would fail the same way, with the same 403.
    return err.code === 'project_locked' ? null : 'init-error'
  }
  if (err instanceof Error) return 'init-error'
  return null
}

/** Forget this session's browser-failure history (all slugs, or one). */
export function resetBrowserFailures(slug?: string): void {
  if (slug) _lastBrowserFailure.delete(slug)
  else _lastBrowserFailure.clear()
}

/** The body `POST /api/render-cancel` wants: whichever ids the stream published. */
export interface RenderCancelTarget {
  request_id?: string
  job_ids?: string[]
}

/**
 * The cancel target for the backend render currently in flight, or null.
 *
 * Exported so a caller that must cancel SYNCHRONOUSLY (page unload) can read the
 * identity without racing a render that starts a moment later — see
 * `cancelRenderOnUnload`.
 */
export function getActiveRenderTarget(): RenderCancelTarget | null {
  const active = _activeRender
  if (!active) return null
  const target: RenderCancelTarget = {}
  if (active.requestId) target.request_id = active.requestId
  if (active.jobIds.length) target.job_ids = active.jobIds
  return Object.keys(target).length > 0 ? target : null
}

/** Read the in-flight target and release the slot, so it cannot be cancelled twice. */
function takeActiveRenderTarget(): RenderCancelTarget | null {
  const target = getActiveRenderTarget()
  if (target) _activeRender = null
  return target
}

/**
 * POST one cancel target. Awaited — for the unload path use `cancelRenderOnUnload`.
 */
async function postCancel(target: RenderCancelTarget | null): Promise<void> {
  if (!target) return
  try {
    await apiFetch(`${API_BASE}/api/render-cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(target)
    })
  } catch { /* best-effort cancel */ }
}

/**
 * Cancel the current render.
 *
 * The server cancels only the jobs it is handed, so this sends the identity the
 * stream published for the render in flight. With nothing in flight — a browser
 * (WASM) render, or a backend render that has already finished — there is no
 * target and the request is skipped: `POST /api/render-cancel` with no target is
 * a 400, and the cancel-everything behaviour it used to have was the bug.
 */
export async function cancelRender(): Promise<void> {
  await postCancel(takeActiveRenderTarget())

  disposeWorker()
}

/**
 * Cancel the in-flight render because a new one is replacing it.
 *
 * Returns true when a cancel was sent. The target is taken (read and cleared)
 * SYNCHRONOUSLY, before the caller opens the new stream, so this can never
 * cancel the render that supersedes it — the new stream publishes its own `job`
 * event into a slot this call has already emptied.
 *
 * Without it, a user dragging a slider left a trail of abandoned renders in
 * front of a single worker, each one delaying the render they actually wanted.
 */
export function cancelSupersededRender(): boolean {
  const target = takeActiveRenderTarget()
  if (!target) return false
  void postCancel(target)
  return true
}

/**
 * SYNCHRONOUS best-effort cancel for a page that is going away.
 *
 * Returns true when a cancel was handed to the browser, false when there was
 * nothing in flight to cancel.
 *
 * WHY THIS EXISTS. Nightly run #171 navigated ~95 times in 40 minutes and
 * produced ZERO `render-cancel` calls: `pagehide` gives a page no chance to
 * await a `fetch`, so every abandoned render kept running. Against a single
 * render worker that is not merely wasteful — the abandoned work sits in front
 * of a live user's render, and the queue starves.
 *
 * WHY sendBeacon FIRST. It is the only transport the browser promises to
 * deliver after the document is gone; a normal `fetch` is cancelled with the
 * page. `keepalive: true` is the documented fallback and is honoured by modern
 * browsers, but it is capped (64 KiB across all keepalive requests) and is not
 * available everywhere `sendBeacon` is, so it is second, not first.
 *
 * WHY THE CONTENT TYPE IS TRIED TWICE. `sendBeacon(url, string)` sends
 * `text/plain`; a Blob lets the beacon carry `application/json`, which is the
 * honest type for the body. But `application/json` is not CORS-safelisted, so
 * cross-origin (`VITE_API_BASE` pointing at api.yantra4d.com) it needs a
 * preflight that a beacon may not get. `text/plain` is a simple request and
 * always goes. So: JSON first, `text/plain` if the queue refuses it, then
 * keepalive fetch. `POST /api/render-cancel` parses either
 * (`routes/engine/render.py::_cancel_body`) — the body is still JSON, only the
 * header differs.
 *
 * No Authorization header is possible on a beacon, so this arrives anonymous.
 * That is fine and by design: the cancel is scoped to the ids the server itself
 * published on this client's stream, which is the entitlement (see docs/AUTH.md
 * § Cancelling a render). It grants an anonymous caller nothing it did not
 * already hold.
 */
export function cancelRenderOnUnload(): boolean {
  const target = takeActiveRenderTarget()
  if (!target) return false

  const url = `${API_BASE}/api/render-cancel`
  const body = JSON.stringify(target)

  if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
    for (const type of ['application/json', 'text/plain;charset=UTF-8']) {
      try {
        if (navigator.sendBeacon(url, new Blob([body], { type }))) return true
      } catch { /* try the next content type, then the fetch fallback */ }
    }
  }

  try {
    // Not awaited: the page is unloading and there is nothing to await it with.
    void fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive: true,
    })
    return true
  } catch {
    return false
  }
}

/**
 * Estimate render time (pure JS, from manifest constants).
 *
 * `placement` names which side the estimate is FOR. The placement decision has
 * to ask "how long would this take in the BROWSER?" before any placement has
 * been chosen, so it passes 'browser' explicitly; callers that just want to
 * warn the user pass nothing and get the estimate for wherever this cartridge
 * is currently headed.
 *
 * The old code answered the same question by mutating the module-global
 * `_hardwareMode` to 'backend', calling itself, and putting the global back —
 * a temporary global write inside a "pure" estimator, and racy the moment two
 * renders overlapped.
 */
export function estimateRenderTime(
  mode: string,
  params: Record<string, unknown>,
  manifest: Manifest,
  placement?: Placement,
): number {
  const constants = manifest.estimate_constants
  if (!constants) return 0

  const modeConfig = manifest.modes.find(m => m.id === mode)
  if (!modeConfig) return 0

  // UNITS. `formula_vars` is a PRODUCT of the named params, so a mode whose cost
  // scales with N^2 lists N twice. That is not a trick: it is the only thing the
  // reducer below can express, and it keeps `base_units` (documentation) and the
  // computed value in agreement.
  //
  // They used to disagree. The cube mode declared `base_units: "N * N"` while
  // listing `formula_vars: ["N"]`, so the estimator computed N and the manifest
  // claimed N^2 — and nothing reconciled them, because `base_units` is only read
  // in the `else` branch and only when it is a NUMBER. A string like "N * N"
  // could never satisfy `typeof base === 'number'`, so the declared intent was
  // unreachable code that read as configuration.
  //
  // Measured 2026-08-08 in the browser (WASM), from the app's own
  // "Total rendering time" lines:
  //     3x3 -> 0.196 s   (units N^2 = 9)
  //     5x5 -> 0.607 s   (units N^2 = 25)
  // Ratio 3.10x observed against 2.78x predicted by N^2 — the manifest's declared
  // model was right and the code was wrong. N alone predicts 1.67x, which the
  // measurement rules out.
  let units = 1
  if (modeConfig.estimate?.formula_vars) {
    units = modeConfig.estimate.formula_vars.reduce((acc, v) => acc * (Number(params[v]) || 1), 1)
  } else {
    const base = modeConfig.estimate?.base_units
    units = (typeof base === 'number') ? base : 1
  }

  const numParts = modeConfig.parts.length
  const estimate = constants.base_time + (units * constants.per_unit) + (numParts * constants.per_part)

  // The browser is typically slower than native.
  const effective: Placement = placement
    ?? _placementBySlug.get(manifestSlug(manifest))
    ?? (isBrowserRenderPossible() ? 'browser' : 'server')
  if (effective === 'browser') {
    return estimate * (constants.wasm_multiplier || 3)
  }
  return estimate
}

/**
 * Get current render mode for diagnostics, in the legacy `'backend' | 'wasm'`
 * vocabulary. Returns the most recently decided placement for any cartridge,
 * or 'detecting' before the first decision.
 */
export function getRenderMode(): string {
  const last = [..._placementBySlug.values()].pop()
  return last ? placementToLegacyMode(last) : 'detecting'
}

/** Current placement for a slug, or null before its first render. */
export function getRenderPlacement(slug: string): Placement | null {
  return _placementBySlug.get(slug) ?? null
}

/** Test seam: forget every per-slug placement decision and failure. */
export function resetPlacementState(): void {
  _placementBySlug.clear()
  _decisionBySlug.clear()
  _lastBrowserFailure.clear()
}

/**
 * Wall-clock seconds of the last completed WASM render, compile INCLUDED.
 *
 * `estimateRenderTime` predicts this exact quantity. Until this existed nothing
 * compared the two, which is how constants that overshot by 1,714x shipped and
 * stayed: the estimator drove a blocking dialog on every render and no surface
 * ever contradicted it. Returns null before the first render completes — a
 * missing measurement must read as missing, never as zero.
 */
export function getLastObservedRenderSeconds(): number | null {
  return _lastObservedRenderSeconds
}

/**
 * How far off the estimate was, as a ratio (estimate / observed).
 *
 * 1.0 is perfect; >1 overshoots. Null when either side is unknown, so a caller
 * cannot mistake "not measured yet" for "accurate".
 */
export function getEstimateAccuracy(estimateSeconds: number): number | null {
  if (_lastObservedRenderSeconds == null || _lastObservedRenderSeconds <= 0) return null
  if (!Number.isFinite(estimateSeconds) || estimateSeconds <= 0) return null
  return estimateSeconds / _lastObservedRenderSeconds
}
