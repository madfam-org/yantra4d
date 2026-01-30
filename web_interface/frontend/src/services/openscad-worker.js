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
 */

import { createOpenSCAD } from 'openscad-wasm'

let openscadInstance = null
let scadFilesLoaded = false

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

async function handleInit({ scadFiles }) {
  try {
    const wrapper = await createOpenSCAD({
      noInitialRun: true,
      printErr: (text) => {
        const phase = detectPhase(text)
        if (phase || isLogWorthy(text)) {
          self.postMessage({ type: 'progress', phase, line: text })
        }
      }
    })
    openscadInstance = wrapper.getInstance()

    // Fetch and write SCAD source files to the Emscripten virtual FS
    const baseUrl = self.location.origin + (import.meta.env?.BASE_URL || '/')
    const files = scadFiles || []
    for (const name of files) {
      const response = await fetch(`${baseUrl}scad/${name}`)
      if (!response.ok) throw new Error(`Failed to fetch ${name}: ${response.status}`)
      const content = await response.text()
      openscadInstance.FS.writeFile(`/${name}`, content)
    }
    scadFilesLoaded = true

    self.postMessage({ type: 'init-done' })
  } catch (e) {
    self.postMessage({ type: 'init-error', error: e.message })
  }
}

function handleRender({ scadFile, params, renderMode }) {
  if (!openscadInstance || !scadFilesLoaded) {
    self.postMessage({ type: 'error', message: 'OpenSCAD not initialized' })
    return
  }

  try {
    const outFile = '/output.stl'

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

    const exitCode = openscadInstance.callMain(args)

    if (exitCode !== 0) {
      self.postMessage({ type: 'error', message: `OpenSCAD exited with code ${exitCode}` })
      return
    }

    const stl = openscadInstance.FS.readFile(outFile, { encoding: 'binary' })
    self.postMessage({ type: 'result', stl }, [stl.buffer])

    try { openscadInstance.FS.unlink(outFile) } catch { /* cleanup */ }
  } catch (e) {
    self.postMessage({ type: 'error', message: e.message || String(e) })
  }
}

self.onmessage = (e) => {
  const { type } = e.data
  if (type === 'init') handleInit(e.data)
  else if (type === 'render') handleRender(e.data)
}
