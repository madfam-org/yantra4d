/**
 * Web Worker for running OpenSCAD WASM via the openscad-wasm npm package.
 *
 * Messages IN:
 *   { type: 'init' }                  - Load WASM module + SCAD source files
 *   { type: 'render', scadFile, params, renderMode }  - Run OpenSCAD render
 *
 * Messages OUT:
 *   { type: 'init-done' }
 *   { type: 'init-error', error }
 *   { type: 'progress', percent, phase, line }
 *   { type: 'result', stl: Uint8Array }   (transferred)
 *   { type: 'error', message }
 *
 * NOTE: Emscripten's callMain() corrupts internal state after the first call,
 * so we create a fresh WASM instance for every render. SCAD file contents are
 * cached in memory so re-initialization is fast (no re-fetch).
 */

import { createOpenSCAD } from 'openscad-wasm'

/** Cached SCAD file contents: Map<filename, string> */
let scadFileCache = new Map()
let initialized = false

export function detectPhase(line) {
  if (line.includes('Compiling')) return 'compiling'
  if (line.includes('CGAL')) return 'cgal'
  if (line.includes('Rendering') || line.includes('Geometries')) return 'rendering'
  if (line.includes('Parsing')) return 'geometry'
  return null
}

export function isLogWorthy(line) {
  return line.includes('Compiling') || line.includes('Parsing') ||
    line.includes('CGAL') || line.includes('Geometries') ||
    line.includes('Rendering') || line.includes('Total') ||
    line.includes('Simple:')
}

/**
 * Create a fresh OpenSCAD WASM instance and write cached SCAD files to its FS.
 */
async function createFreshInstance() {
  const wrapper = await createOpenSCAD({
    noInitialRun: true,
    printErr: (text) => {
      const phase = detectPhase(text)
      if (phase || isLogWorthy(text)) {
        self.postMessage({ type: 'progress', phase, line: text })
      }
    }
  })
  const instance = wrapper.getInstance()

  // Write cached SCAD files to the new instance's virtual FS
  for (const [name, content] of scadFileCache) {
    instance.FS.writeFile(`/${name}`, content)
  }

  return instance
}

async function handleInit({ scadFiles }) {
  try {
    // Fetch and cache SCAD source files
    const baseUrl = self.location.origin + (import.meta.env?.BASE_URL || '/')
    const files = scadFiles || []
    for (const name of files) {
      const response = await fetch(`${baseUrl}scad/${name}`)
      if (!response.ok) throw new Error(`Failed to fetch ${name}: ${response.status}`)
      const content = await response.text()
      scadFileCache.set(name, content)
    }

    // Verify we can create an instance (fail-fast)
    await createFreshInstance()

    initialized = true
    self.postMessage({ type: 'init-done' })
  } catch (e) {
    self.postMessage({ type: 'init-error', error: e.message })
  }
}

async function handleRender({ scadFile, params, renderMode }) {
  if (!initialized) {
    self.postMessage({ type: 'error', message: 'OpenSCAD not initialized' })
    return
  }

  try {
    const outFile = '/output.stl'

    // Create a fresh WASM instance for this render (avoids callMain reuse crash)
    const instance = await createFreshInstance()

    // Build command-line args
    const args = [`/${scadFile}`]

    for (const [key, value] of Object.entries(params)) {
      if (typeof value === 'boolean') {
        args.push('-D', `${key}=${value ? 'true' : 'false'}`)
      } else {
        args.push('-D', `${key}=${value}`)
      }
    }

    args.push('-D', `render_mode=${renderMode}`)
    args.push('--enable=manifold')
    args.push('-o', outFile)

    self.postMessage({ type: 'progress', percent: 10, phase: 'compiling', line: 'Starting OpenSCAD...' })

    const exitCode = instance.callMain(args)

    if (exitCode !== 0) {
      self.postMessage({ type: 'error', message: `OpenSCAD exited with code ${exitCode}` })
      return
    }

    const stl = instance.FS.readFile(outFile, { encoding: 'binary' })
    self.postMessage({ type: 'result', stl }, [stl.buffer])
  } catch (e) {
    self.postMessage({ type: 'error', message: e.message || String(e) })
  }
}

self.onmessage = (e) => {
  const { type } = e.data
  if (type === 'init') handleInit(e.data)
  else if (type === 'render') handleRender(e.data)
}
