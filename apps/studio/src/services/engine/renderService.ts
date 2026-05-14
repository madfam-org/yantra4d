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
}

const API_BASE = getApiBase()

let _hardwareMode: 'backend' | 'wasm' | null = null
let _worker: Worker | null = null
let _initPromise: Promise<void> | null = null

/**
 * Detect hardware capabilities
 */
function hasWasmCapabilities(): boolean {
  const cores = navigator.hardwareConcurrency || 2
  const mem = (navigator as { deviceMemory?: number }).deviceMemory || 4
  return cores >= 4 && mem >= 4
}

/**
 * Detect whether to use 'backend' or 'wasm' rendering mode.
 * Checks backend availability BEFORE respecting force_backend/API_BASE preferences,
 * so the app can fall back to WASM when the backend is unreachable.
 */
async function detectMode(manifest: Manifest | null, mode: string, params: Record<string, unknown>): Promise<'backend' | 'wasm'> {
  // CadQuery engine has no WASM path — always backend
  if (manifest && manifest.engine === 'cadquery') {
    return 'backend'
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
 * Check whether the current manifest supports client-side WASM rendering.
 */
export function canRunWasm(manifest: Manifest | null): boolean {
  return manifest?.engine !== 'cadquery' && manifest?.engine !== 'implicit'
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

    onProgress?.({
      percent: Math.round(((i + 1) / totalParts) * 100),
      phase: 'done',
      part: partId,
      log: `[${partId}] Done (${Math.round(((i + 1) / totalParts) * 100)}%)`
    })
  }

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
  exportFormat?: string
): Promise<RenderPart[]> {
  const payload: Record<string, unknown> = { ...params, mode }
  if (project) payload.project = project
  if (ignoreCache) payload.ignore_cache = true

  if (exportFormat) {
    payload.export_format = exportFormat
  } else if (manifest && manifest.engine === 'cadquery') {
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

  const processEvent = (data: SSEData) => {
    if (data.progress !== undefined) {
      onProgress?.({ percent: data.progress })
    }

    if (data.event === 'part_start') {
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
      onProgress?.({
        part: data.part,
        log: `[${data.part}] Done (${data.progress}%)`
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
  { onProgress, abortSignal, project, ignoreCache, exportFormat }: RenderOptions = {}
): Promise<RenderPart[]> {
  const currentMode = await detectMode(manifest, mode, params)
  if (currentMode === 'backend') {
    try {
      return await renderBackend(mode, params, manifest, onProgress, abortSignal, project, ignoreCache, exportFormat)
    } catch (err) {
      // If backend fails with network/capacity errors, try WASM fallback.
      const forceBackend = manifest?.project?.force_backend || manifest?.force_backend
      const canFallbackToWasm = (
        !forceBackend
        && manifest?.engine !== 'cadquery'
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

/**
 * Cancel the current render.
 */
export async function cancelRender(): Promise<void> {
  try {
    await apiFetch(`${API_BASE}/api/render-cancel`, { method: 'POST' })
  } catch { /* best-effort cancel */ }

  if (_worker) {
    _worker.terminate()
    _worker = null
    _initPromise = null
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
