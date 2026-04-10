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
import type { OpenSCAD } from 'openscad-wasm'
import { detectPhase, isLogWorthy } from '../../lib/openscad-phases'

declare const self: {
  postMessage(message: unknown, transfer?: Transferable[]): void
  location: { origin: string }
  onmessage: ((ev: MessageEvent) => void) | null
}

type WorkerMessageIn =
  | { type: 'init'; scadFiles?: string[] }
  | { type: 'render'; scadFile: string; params: Record<string, unknown>; renderMode: number }

type WorkerMessageOut =
  | { type: 'init-done' }
  | { type: 'init-error'; error: string }
  | { type: 'progress'; percent?: number; phase?: string | null; line: string }
  | { type: 'result'; stl: Uint8Array }
  | { type: 'error'; message: string }

const scadFileCache: Map<string, string> = new Map()
let initialized = false

async function createFreshInstance(): Promise<OpenSCAD> {
  const wrapper = await createOpenSCAD({
    noInitialRun: true,
    TOTAL_MEMORY: 536870912, // 512MB
    ALLOW_MEMORY_GROWTH: 1,
    printErr: (text: string) => {
      const phase = detectPhase(text)
      if (phase || isLogWorthy(text)) {
        self.postMessage({ type: 'progress', phase, line: text } satisfies WorkerMessageOut)
      }
    }
  } as Parameters<typeof createOpenSCAD>[0])
  const instance = wrapper.getInstance()

  // Write cached SCAD files to the new instance's virtual FS
  for (const [name, content] of scadFileCache) {
    instance.FS.writeFile(`/${name}`, content)
  }

  return instance
}

async function handleInit({ scadFiles }: Extract<WorkerMessageIn, { type: 'init' }>): Promise<void> {
  try {
    // Fetch and cache SCAD source files
    const baseUrl = self.location.origin + ((import.meta as { env?: { BASE_URL?: string } }).env?.BASE_URL || '/')
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
    self.postMessage({ type: 'init-done' } satisfies WorkerMessageOut)
  } catch (e) {
    self.postMessage({ type: 'init-error', error: (e as Error).message } satisfies WorkerMessageOut)
  }
}

async function handleRender({ scadFile, params, renderMode }: Extract<WorkerMessageIn, { type: 'render' }>): Promise<void> {
  if (!initialized) {
    self.postMessage({ type: 'error', message: 'OpenSCAD not initialized' } satisfies WorkerMessageOut)
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
      } else if (typeof value === 'string') {
        args.push('-D', `${key}="${value}"`)
      } else {
        args.push('-D', `${key}=${value}`)
      }
    }

    args.push('-D', `render_mode=${renderMode}`)
    args.push('--enable=manifold')
    args.push('-o', outFile)

    self.postMessage({ type: 'progress', percent: 10, phase: 'compiling', line: 'Starting OpenSCAD...' } satisfies WorkerMessageOut)

    const exitCode = instance.callMain(args)

    if (exitCode !== 0) {
      self.postMessage({ type: 'error', message: `OpenSCAD exited with code ${exitCode}` } satisfies WorkerMessageOut)
      return
    }

    const stl = instance.FS.readFile(outFile, { encoding: 'binary' })
    self.postMessage({ type: 'result', stl } satisfies WorkerMessageOut, [stl.buffer])
  } catch (e) {
    self.postMessage({ type: 'error', message: (e as Error).message || String(e) } satisfies WorkerMessageOut)
  }
}

self.onmessage = (e: MessageEvent<WorkerMessageIn>) => {
  const { type } = e.data
  if (type === 'init') handleInit(e.data)
  else if (type === 'render') handleRender(e.data)
}
