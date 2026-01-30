/**
 * Render service with dual-mode support:
 * - Backend mode: uses Flask API (native OpenSCAD, faster)
 * - WASM mode: uses openscad-wasm in a Web Worker (for static deploy / GitHub Pages)
 *
 * Auto-detects which mode to use by checking if the backend is reachable.
 */

import { isBackendAvailable, getApiBase } from './backendDetection'

const API_BASE = getApiBase()

let _mode = null // 'backend' | 'wasm'
let _worker = null
let _workerReady = false
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
 */
function initWorker() {
  if (_initPromise) return _initPromise

  _initPromise = new Promise((resolve, reject) => {
    _worker = new Worker(
      new URL('./openscad-worker.js', import.meta.url),
      { type: 'module' }
    )

    const handler = (e) => {
      if (e.data.type === 'init-done') {
        _workerReady = true
        _worker.removeEventListener('message', handler)
        resolve()
      } else if (e.data.type === 'init-error') {
        _worker.removeEventListener('message', handler)
        reject(new Error(e.data.error))
      }
    }
    _worker.addEventListener('message', handler)
    _worker.postMessage({ type: 'init' })
  })

  return _initPromise
}

/**
 * Detect the progress phase from an output line.
 */
function detectPhase(line) {
  if (line.includes('Compiling')) return 'compiling'
  if (line.includes('CGAL')) return 'cgal'
  if (line.includes('Rendering') || line.includes('Geometries')) return 'rendering'
  if (line.includes('Parsing')) return 'geometry'
  return null
}

/**
 * Check if a line is worth logging (contains significant output info).
 */
function isSignificantLine(line) {
  return line.includes('Compiling') || line.includes('Parsing') ||
    line.includes('CGAL') || line.includes('Geometries') ||
    line.includes('Rendering') || line.includes('Total') ||
    line.includes('Simple:')
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
  await initWorker()

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
          _workerReady = false
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
async function renderBackend(mode, params, onProgress, abortSignal) {
  const payload = { ...params, mode }

  const response = await fetch(`${API_BASE}/api/render-stream`, {
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
        if (isSignificantLine(line)) {
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
export async function renderParts(mode, params, manifest, { onProgress, abortSignal } = {}) {
  const currentMode = await detectMode()
  if (currentMode === 'backend') {
    return renderBackend(mode, params, onProgress, abortSignal)
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
      await fetch(`${API_BASE}/api/render-cancel`, { method: 'POST' })
    } catch { /* best-effort cancel */ }
  } else if (_worker) {
    _worker.terminate()
    _worker = null
    _workerReady = false
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
  if (modeConfig.estimate?.formula === 'grid') {
    units = (params.rows || 1) * (params.cols || 1)
  } else {
    units = modeConfig.estimate?.base_units || 1
  }

  const numParts = modeConfig.parts.length
  const estimate = constants.base_time + (units * constants.per_unit) + (numParts * constants.per_part)

  // WASM is typically 2-5x slower than native
  const currentMode = _mode
  if (currentMode === 'wasm') {
    return estimate * 3 // conservative 3x multiplier
  }
  return estimate
}

/**
 * Get current render mode for diagnostics.
 */
export function getRenderMode() {
  return _mode || 'detecting'
}
