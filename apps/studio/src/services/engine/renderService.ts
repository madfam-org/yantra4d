/**
 * Render service with dual-mode support:
 * - Backend mode: uses Flask API (native OpenSCAD, faster)
 * - WASM mode: uses openscad-wasm in a Web Worker (for offline/static deploy)
 *
 * Auto-detects which mode to use by checking if the backend is reachable.
 */

import { isBackendAvailable, getApiBase, resetDetection } from '../core/backendDetection'
import { detectPhase, isLogWorthy } from '../../lib/openscad-phases'
import { apiFetch } from '../core/apiClient'

interface Manifest {
  modes: ModeConfig[]
  parts: PartDef[]
  engine?: string
  project?: { force_backend?: boolean }
  force_backend?: boolean
  estimate_constants?: EstimateConstants
  grid_presets?: Record<string, unknown>
  [key: string]: unknown
}

interface ModeConfig {
  id: string
  scad_file: string
  parts: string[]
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

let _hardwareMode: 'backend' | 'wasm' | null = null
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
 * Detect hardware capabilities
 */
function hasWasmCapabilities(): boolean {
  const cores = navigator.hardwareConcurrency || 2
  const mem = (navigator as { deviceMemory?: number }).deviceMemory || 4
  return cores >= 4 && mem >= 4
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
 *   3. null                                — defer to the hardware heuristic
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

/**
 * Detect whether to use 'backend' or 'wasm' rendering mode.
 *
 * An explicit override (`?render=` / `VITE_RENDER_MODE`) wins over everything
 * below it. Absent one, this checks backend availability BEFORE respecting
 * force_backend/API_BASE preferences, so the app can fall back to WASM when the
 * backend is unreachable.
 */
async function detectMode(manifest: Manifest | null, mode: string, params: Record<string, unknown>): Promise<'backend' | 'wasm'> {
  // Backend-only engines have no WASM path — always backend.
  // Deliberately ABOVE the override: `?render=wasm` on a CadQuery/graph project
  // cannot be honoured (the kernel only exists server-side), and pretending
  // otherwise would trade a working render for a guaranteed failure.
  if (manifest && BACKEND_ONLY_ENGINES.has(manifest.engine ?? '')) {
    return 'backend'
  }

  // Explicit override — consulted BEFORE backend probing and the hardware
  // heuristic, so a pinned path is honoured regardless of core count, of
  // whether /api/health answers, and of force_backend.
  if (RENDER_MODE_OVERRIDE) {
    console.warn(`[Render Mode] Override active: forcing '${RENDER_MODE_OVERRIDE}' rendering (hardware heuristic bypassed).`)
    _hardwareMode = RENDER_MODE_OVERRIDE
    return RENDER_MODE_OVERRIDE
  }

  // Check backend availability first (uses TTL-cached result)
  const available = await isBackendAvailable()

  if (available) {
    // Backend is up — respect preferences, but override if rate-limited and WASM-capable
    if (manifest && (manifest.project?.force_backend || manifest.force_backend)) {
      return 'backend'
    }
    if (API_BASE) {
      return 'backend'
    }
    // Complexity circuit breaker
    if (manifest && mode && params) {
      const tempMode = _hardwareMode
      _hardwareMode = 'backend'
      const est = estimateRenderTime(mode, params, manifest)
      _hardwareMode = tempMode

      if (est > 15.0) {
        console.warn(`[Circuit Breaker] Mesh complexity too high (est. ${est.toFixed(1)}s). Bypassing WASM and falling back to Server Backend.`)
        return 'backend'
      }
    }
    if (_hardwareMode) return _hardwareMode
    _hardwareMode = hasWasmCapabilities() ? 'wasm' : 'backend'
    return _hardwareMode
  }

  // Backend unavailable — fall back to WASM if capable
  if (hasWasmCapabilities()) {
    console.warn('[Fallback] Backend unavailable, falling back to WASM rendering.')
    _hardwareMode = 'wasm'
    return 'wasm'
  }

  // No WASM either — return backend (will fail, but renderBackend will throw with a clear error)
  return 'backend'
}

/**
 * Engines the browser cannot run: CadQuery and graph documents execute
 * server-side kernels (graph transpiles to CadQuery). Implicit is additionally
 * excluded from WASM in canRunWasm but keeps its own detectMode behavior.
 */
const BACKEND_ONLY_ENGINES = new Set(['cadquery', 'graph'])

/**
 * Check whether the current manifest supports client-side WASM rendering.
 */
export function canRunWasm(manifest: Manifest | null): boolean {
  return !BACKEND_ONLY_ENGINES.has(manifest?.engine ?? '') && manifest?.engine !== 'implicit'
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
 * Initialize the WASM worker (lazy, called on first WASM render).
 */
function initWorker(manifest: Manifest | null): Promise<void> {
  if (_initPromise) return _initPromise

  _initPromise = new Promise((resolve, reject) => {
    _worker = new Worker(
      new URL('./openscad-worker.js', import.meta.url),
      { type: 'module' }
    )

    const handler = (e: MessageEvent) => {
      if (e.data.type === 'init-done') {
        _worker!.removeEventListener('message', handler)
        resolve()
      } else if (e.data.type === 'init-error') {
        _worker!.removeEventListener('message', handler)
        reject(new Error(e.data.error))
      }
    }
    _worker.addEventListener('message', handler)

    const scadFiles = manifest
      ? [...new Set(manifest.modes.map(m => m.scad_file))]
      : []
    _worker.postMessage({ type: 'init', scadFiles })
  })

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
  abortSignal?: AbortSignal
): Promise<RenderPart[]> {
  await initWorker(manifest)

  const modeConfig = manifest.modes.find(m => m.id === mode)
  if (!modeConfig) throw new Error(`Unknown mode: ${mode}`)

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
      const handler = (e: MessageEvent) => {
        const msg = e.data
        if (msg.type === 'result') {
          _worker!.removeEventListener('message', handler)
          resolve(msg.stl)
        } else if (msg.type === 'error') {
          _worker!.removeEventListener('message', handler)
          reject(new Error(msg.message))
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
          _worker!.removeEventListener('message', handler)
          _worker!.terminate()
          _worker = null
          _initPromise = null
          reject(new DOMException('Aborted', 'AbortError'))
        }
        abortSignal.addEventListener('abort', onAbort, { once: true })
      }
      _worker!.addEventListener('message', handler)
      _worker!.postMessage({
        type: 'render',
        scadFile: modeConfig.scad_file,
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

  if (_worker) {
    _worker.terminate()
    _worker = null
    _initPromise = null
  }

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
  } else if (manifest && BACKEND_ONLY_ENGINES.has(manifest.engine ?? '')) {
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
 * If backend rendering fails with a network error, falls back to WASM when possible.
 */
export async function renderParts(
  mode: string,
  params: Record<string, unknown>,
  manifest: Manifest,
  { onProgress, abortSignal, project, ignoreCache, exportFormat, onJob }: RenderOptions = {}
): Promise<RenderPart[]> {
  const currentMode = await detectMode(manifest, mode, params)
  if (currentMode === 'backend') {
    try {
      return await renderBackend(mode, params, manifest, onProgress, abortSignal, project, ignoreCache, exportFormat, onJob)
    } catch (err) {
      // If backend fails with network/capacity errors, try WASM fallback.
      const forceBackend = manifest?.project?.force_backend || manifest?.force_backend
      // `?render=backend` is a deliberate "keep me off WASM" instruction —
      // usually because WASM is exactly what broke for this user. Falling back
      // to it here would quietly undo the override at the one moment it matters.
      const canFallbackToWasm = (
        !forceBackend
        && RENDER_MODE_OVERRIDE !== 'backend'
        && !BACKEND_ONLY_ENGINES.has(manifest?.engine ?? '')
        && hasWasmCapabilities()
      )
      const shouldFallback = (
        isNetworkError(err)
        || isRateLimitError(err)
        || isRenderWorkerUnavailableError(err)
      )
      if (canFallbackToWasm && shouldFallback) {
        const isRL = isRateLimitError(err)
        const isWorkerUnavailable = isRenderWorkerUnavailableError(err)
        const reason = isRL ? 'rate limited' : isWorkerUnavailable ? 'worker unavailable' : 'network'
        console.warn(`[Fallback] Backend render failed (${reason}), retrying with WASM:`, (err as Error).message)
        if (!isRL) resetDetection() // clear cached availability so next render re-checks
        _hardwareMode = 'wasm'
        const fallbackLog = isRL
          ? '[FALLBACK] Server limit reached, rendering locally...'
          : isWorkerUnavailable
            ? '[FALLBACK] Render worker unavailable, rendering locally...'
            : '[FALLBACK] Backend unavailable, using browser rendering...'
        onProgress?.({ log: fallbackLog })
        return renderWasm(mode, params, manifest, onProgress, abortSignal)
      }
      // For force_backend projects, provide a clear rate-limit message instead of cryptic WASM failure
      if (forceBackend && isRateLimitError(err)) {
        onProgress?.({ log: '[ERROR] Server render limit reached. This project requires server rendering — upgrade your plan or wait for the limit to reset.' })
      }
      if (forceBackend && isRenderWorkerUnavailableError(err)) {
        onProgress?.({ log: '[ERROR] Server render worker is unavailable. This project requires server rendering — retry after the render service recovers.' })
      }
      throw err // re-throw non-recoverable errors
    }
  } else {
    return renderWasm(mode, params, manifest, onProgress, abortSignal)
  }
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

  if (_worker) {
    _worker.terminate()
    _worker = null
    _initPromise = null
  }
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
 */
export function estimateRenderTime(mode: string, params: Record<string, unknown>, manifest: Manifest): number {
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

  // WASM is typically slower than native
  const currentMode = _hardwareMode || (hasWasmCapabilities() ? 'wasm' : 'backend')
  if (currentMode === 'wasm') {
    return estimate * (constants.wasm_multiplier || 3)
  }
  return estimate
}

/**
 * Get current render mode for diagnostics.
 */
export function getRenderMode(): string {
  return _hardwareMode || 'detecting'
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
