/**
 * Render service with dual-mode support:
 * - Backend mode: uses Flask API (native OpenSCAD, faster)
 * - WASM mode: uses openscad-wasm in a Web Worker (for offline/static deploy)
 *
 * Auto-detects which mode to use by checking if the backend is reachable.
 */

import { isBackendAvailable, getApiBase } from './backendDetection'
import { detectPhase, isLogWorthy } from '../lib/openscad-phases'
import { apiFetch } from './apiClient'

const API_BASE = getApiBase()

let _mode = null // 'backend' | 'wasm'
let _worker = null
let _initPromise = null

/**
 * Detect whether backend is available. Caches result.
 */
async function detectMode() {
  if (_mode) return _mode
  const available = await isBackendAvailable()
  _mode = available ? 'backend' : 'wasm'
  return _mode
}

/**
 * Initialize the WASM worker (lazy, called on first WASM render).
 * @param {object} [manifest] - Project manifest to extract SCAD file list from
 */
function initWorker(manifest) {
  if (_initPromise) return _initPromise

  _initPromise = new Promise((resolve, reject) => {
    _worker = new Worker(
      new URL('./openscad-worker.js', import.meta.url),
      { type: 'module' }
    )

    const handler = (e) => {
      if (e.data.type === 'init-done') {
        _worker.removeEventListener('message', handler)
        resolve()
      } else if (e.data.type === 'init-error') {
        _worker.removeEventListener('message', handler)
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

/**
 * Parse a raw SSE chunk string into individual JSON data objects.
 */
function parseSSEChunk(chunk) {
  const lines = chunk.split('\n').filter(line => line.startsWith('data: '))
  const results = []
  for (const rawLine of lines) {
    try {
      results.push(JSON.parse(rawLine.slice(6)))
    } catch (e) {
      console.warn('Malformed SSE data:', e)
    }
  }
  return results
}

/**
 * Render parts via WASM worker.
 * Returns array of { type, blob, url } for each part.
 */
async function renderWasm(mode, params, manifest, onProgress, abortSignal) {
  await initWorker(manifest)

  const modeConfig = manifest.modes.find(m => m.id === mode)
  if (!modeConfig) throw new Error(`Unknown mode: ${mode}`)

  const parts = []
  const totalParts = modeConfig.parts.length

  for (let i = 0; i < totalParts; i++) {
    if (abortSignal?.aborted) throw new DOMException('Aborted', 'AbortError')
    const partId = modeConfig.parts[i]
    const partDef = manifest.parts.find(p => p.id === partId)
    if (!partDef) continue

    const basePercent = Math.round((i / totalParts) * 100)
    onProgress?.({
      percent: basePercent,
      phase: 'compiling',
      part: partId,
      log: `[${partId}] Starting... (${i + 1}/${totalParts})`
    })

    const stlData = await new Promise((resolve, reject) => {
      const handler = (e) => {
        const msg = e.data
        if (msg.type === 'result') {
          _worker.removeEventListener('message', handler)
          resolve(msg.stl)
        } else if (msg.type === 'error') {
          _worker.removeEventListener('message', handler)
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
          _worker.removeEventListener('message', handler)
          _worker.terminate()
          _worker = null
          _initPromise = null
          reject(new DOMException('Aborted', 'AbortError'))
        }
        abortSignal.addEventListener('abort', onAbort, { once: true })
      }
      _worker.addEventListener('message', handler)
      _worker.postMessage({
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

  return parts
}

/**
 * Render parts via backend SSE stream.
 * Returns array of { type, url } for each part.
 */
async function renderBackend(mode, params, onProgress, abortSignal, project) {
  const payload = { ...params, mode }
  if (project) payload.project = project

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

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let finalParts = []

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value, { stream: true })
    const events = parseSSEChunk(chunk)

    for (const data of events) {
      if (data.progress !== undefined) {
        onProgress?.({ percent: data.progress })
      }

      if (data.event === 'part_start') {
        onProgress?.({
          part: data.part,
          log: `[${data.part}] Starting... (${data.index + 1}/${data.total})`
        })
      } else if (data.event === 'output') {
        const line = data.line
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
        finalParts = data.parts
      } else if (data.event === 'error') {
        onProgress?.({ log: `[ERROR] ${data.part}: ${data.message}` })
      }
    }
  }

  if (finalParts.length === 0) {
    throw new Error('Render stream completed without producing any parts')
  }

  const timestamp = Date.now()
  return finalParts.map(p => ({
    ...p,
    url: p.url + '?t=' + timestamp
  }))
}

/**
 * Main entry point: render parts for the given mode and parameters.
 */
export async function renderParts(mode, params, manifest, { onProgress, abortSignal, project } = {}) {
  const currentMode = await detectMode()
  if (currentMode === 'backend') {
    return renderBackend(mode, params, onProgress, abortSignal, project)
  } else {
    return renderWasm(mode, params, manifest, onProgress, abortSignal)
  }
}

/**
 * Cancel the current render.
 */
export async function cancelRender() {
  const currentMode = await detectMode()
  if (currentMode === 'backend') {
    try {
      await apiFetch(`${API_BASE}/api/render-cancel`, { method: 'POST' })
    } catch { /* best-effort cancel */ }
  } else if (_worker) {
    _worker.terminate()
    _worker = null
    _initPromise = null
  }
}

/**
 * Estimate render time (pure JS, from manifest constants).
 */
export function estimateRenderTime(mode, params, manifest) {
  const constants = manifest.estimate_constants
  if (!constants) return 0

  const modeConfig = manifest.modes.find(m => m.id === mode)
  if (!modeConfig) return 0

  let units = 1
  if (modeConfig.estimate?.formula_vars) {
    units = modeConfig.estimate.formula_vars.reduce((acc, v) => acc * (params[v] || 1), 1)
  } else {
    const base = modeConfig.estimate?.base_units
    units = (typeof base === 'number') ? base : 1
  }

  const numParts = modeConfig.parts.length
  const estimate = constants.base_time + (units * constants.per_unit) + (numParts * constants.per_part)

  // WASM is typically slower than native
  const currentMode = _mode
  if (currentMode === 'wasm') {
    return estimate * (constants.wasm_multiplier || 3)
  }
  return estimate
}

/**
 * Get current render mode for diagnostics.
 */
export function getRenderMode() {
  return _mode || 'detecting'
}
