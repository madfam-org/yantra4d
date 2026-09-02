/**
 * Web Worker running OpenSCAD WASM via the `openscad-wasm` package.
 *
 * Messages IN:
 *   { type: 'init', bundle }                          - mount a wasm-bundle in the virtual FS
 *   { type: 'render', entryPath, params, renderMode }  - run OpenSCAD
 *   { type: 'benchmark' }                             - instantiate + tiny reference render
 *
 * Messages OUT:
 *   { type: 'init-done', fileCount, fontCount }
 *   { type: 'init-error', error, kind }
 *   { type: 'progress', percent, phase, line }
 *   { type: 'result', stl }                            (transferred)
 *   { type: 'error', message, kind }
 *   { type: 'benchmark-done', ms }
 *
 * FAILURE KINDS. `kind` is what `renderParts()` reads to decide whether falling
 * back to the server is worth anything:
 *   'init-error' - the module would not instantiate, or the bundle would not mount
 *   'oom'        - the tab ran out of memory
 *   'timeout'    - enforced by the caller (see below), never raised here
 *   'scad-error' - OpenSCAD compiled the model and rejected it
 * Only the first three are worth retrying on the server. A SCAD syntax error is
 * the same source code either way: retrying it server-side spends a quota unit
 * to reproduce the identical message.
 *
 * WHY THE TIMEOUT LIVES IN THE CALLER. `instance.callMain()` is a synchronous
 * call into WASM. While it runs, this worker's event loop is blocked, so a
 * `setTimeout` armed here could not possibly fire. The only thing that can stop
 * a runaway render is `worker.terminate()` from the main thread — so the clock
 * runs there, and this file has no timeout logic at all.
 *
 * NOTE: Emscripten's `callMain()` corrupts internal state after the first call,
 * so every render gets a fresh WASM instance. The bundle is kept in worker
 * memory and re-mounted each time, which costs a few ms of `FS.writeFile`.
 */

import { createOpenSCAD } from 'openscad-wasm'
import type { OpenSCAD } from 'openscad-wasm'
import { detectPhase, isLogWorthy } from '../../lib/openscad-phases'
import {
  planBundleFsLayout,
  FONTCONFIG_PATH,
  FONT_DIR,
  VIRTUAL_OPENSCADPATH,
  type BundleFsLayout,
  type WasmBundle,
} from './wasmBundle'

declare const self: {
  postMessage(message: unknown, transfer?: Transferable[]): void
  location: { origin: string }
  onmessage: ((ev: MessageEvent) => void) | null
}

export type RenderFailureKind = 'init-error' | 'oom' | 'timeout' | 'scad-error'

type WorkerMessageIn =
  | { type: 'init'; bundle: WasmBundle }
  | { type: 'render'; entryPath: string; params: Record<string, unknown>; renderMode: number }
  | { type: 'benchmark' }

type WorkerMessageOut =
  | { type: 'init-done'; fileCount: number; fontCount: number }
  | { type: 'init-error'; error: string; kind: RenderFailureKind }
  | { type: 'progress'; percent?: number; phase?: string | null; line: string }
  | { type: 'result'; stl: Uint8Array }
  | { type: 'error'; message: string; kind: RenderFailureKind }
  | { type: 'benchmark-done'; ms: number }

/**
 * The reference render the capability probe times. Small, deterministic, and
 * dominated by module instantiation rather than by geometry.
 */
const BENCHMARK_SOURCE = '$fn=64; cube(10);'

let layout: BundleFsLayout | null = null
let fontBytes: Map<string, Uint8Array> = new Map()

/** Base64 -> bytes. Fonts arrive base64'd because JSON has no binary type. */
function decodeBase64(base64: string): Uint8Array {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

/**
 * Emscripten exposes `ENV` for setenv-style configuration; the package's
 * published types do not declare it, so it is reached through this shape.
 */
interface InstanceWithEnv extends OpenSCAD {
  ENV?: Record<string, string>
}

function classifyThrown(err: unknown): RenderFailureKind {
  const message = err instanceof Error ? err.message : String(err ?? '')
  if (/out of memory|\bOOM\b|Cannot enlarge memory|allocation failed|Array buffer allocation failed/i.test(message)) {
    return 'oom'
  }
  if (err instanceof RangeError) return 'oom'
  return 'init-error'
}

async function createFreshInstance(mountBundle: boolean): Promise<InstanceWithEnv> {
  const plan = mountBundle ? layout : null
  const wrapper = await createOpenSCAD({
    noInitialRun: true,
    TOTAL_MEMORY: 536870912, // 512MB
    ALLOW_MEMORY_GROWTH: 1,
    // THE MOUNT RUNS IN preRun, NOT AFTER INSTANTIATION.
    //
    // `OPENSCADPATH` is read through `getenv()`, and Emscripten materialises the
    // environment once during startup. Assigning `instance.ENV.OPENSCADPATH`
    // after `createOpenSCAD()` resolves is therefore too late: measured against
    // this exact build, `include <BOSL2/std.scad>` (the search-path form, as
    // opposed to the relative `../../libs/...` form) failed with "Can't open
    // include file" when ENV was set afterwards and rendered a 19,073-byte STL
    // when the same assignment happened in preRun. FONTCONFIG_FILE happens to
    // survive the late assignment; OPENSCADPATH does not, and relying on that
    // difference would be relying on an accident. Mounting the files here too
    // keeps one code path instead of two.
    preRun: plan
      ? [(mod: InstanceWithEnv) => mountLayout(mod, plan)]
      : undefined,
    printErr: (text: string) => {
      const phase = detectPhase(text)
      if (phase || isLogWorthy(text)) {
        self.postMessage({ type: 'progress', phase, line: text } satisfies WorkerMessageOut)
      }
    },
  } as Parameters<typeof createOpenSCAD>[0])
  return wrapper.getInstance() as InstanceWithEnv
}

/**
 * Write a planned layout into a fresh module's virtual filesystem.
 *
 * Called from `preRun` — see `createFreshInstance` for why that matters.
 *
 * Directory order matters: `FS.mkdir` does not create intermediates, which is
 * why `planBundleFsLayout` returns them shallowest-first. `mkdir` on an
 * existing directory throws, and that is fine to swallow — the plan may list a
 * directory a previous entry already created.
 */
function mountLayout(instance: InstanceWithEnv, plan: BundleFsLayout): void {
  for (const dir of plan.dirs) {
    try {
      instance.FS.mkdir(dir)
    } catch { /* already exists */ }
  }
  for (const file of plan.files) {
    instance.FS.writeFile(file.path, file.text)
  }

  // OPENSCADPATH must mirror what the server searched when it resolved this
  // bundle. Relative includes need nothing set, but `include <BOSL2/std.scad>`
  // and `include <dotSCAD/src/…>` resolve through the search path — and a
  // browser searching different directories, or the same ones in a different
  // order, would render a different model than the server does from identical
  // source. Proven against this build: 19,073-byte STL with it, "Can't open
  // include file 'BOSL2/std.scad'" without.
  if (instance.ENV) instance.ENV.OPENSCADPATH = VIRTUAL_OPENSCADPATH

  if (plan.fontsConf) {
    for (const font of plan.fonts) {
      const bytes = fontBytes.get(font.path)
      if (bytes) instance.FS.writeFile(font.path, bytes)
    }
    // The document itself comes from the bundle (the API generates it with the
    // same `fontconfig_xml()` the native renderer uses, already pointed at the
    // virtual font directories); planBundleFsLayout only synthesises one for
    // the dev-only /scad/ fallback.
    instance.FS.writeFile(FONTCONFIG_PATH, plan.fontsConf)
    // Without FONTCONFIG_FILE the build aborts every text() with
    // "Fontconfig error: Cannot load default config file: No such file: (null)"
    // and renders the model minus its lettering, at exit code 0. Measured.
    if (instance.ENV) {
      instance.ENV.FONTCONFIG_FILE = FONTCONFIG_PATH
      instance.ENV.FONTCONFIG_PATH = FONT_DIR
    }
  }
}

async function handleInit({ bundle }: Extract<WorkerMessageIn, { type: 'init' }>): Promise<void> {
  try {
    const plan = planBundleFsLayout(bundle)
    fontBytes = new Map()
    for (const font of plan.fonts) {
      fontBytes.set(font.path, decodeBase64(font.base64))
    }
    layout = plan

    // Fail fast: instantiate once now so an unusable WASM environment surfaces
    // as init-error (server-worthy) rather than as a mid-render mystery.
    await createFreshInstance(true)

    self.postMessage({
      type: 'init-done',
      fileCount: plan.files.length,
      fontCount: plan.fonts.length,
    } satisfies WorkerMessageOut)
  } catch (e) {
    layout = null
    self.postMessage({
      type: 'init-error',
      error: (e as Error).message || String(e),
      kind: classifyThrown(e),
    } satisfies WorkerMessageOut)
  }
}

function buildArgs(
  entryPath: string,
  params: Record<string, unknown>,
  renderMode: number,
  outFile: string,
): string[] {
  const args = [entryPath]
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
  // Kept for forward compatibility with a Manifold-enabled build. The shipped
  // openscad-wasm@0.0.4 answers "WARNING: Ignoring request to enable unknown
  // feature 'manifold'" and falls through to CGAL — measured, harmless.
  args.push('--enable=manifold')
  args.push('-o', outFile)
  return args
}

async function handleRender(
  { entryPath, params, renderMode }: Extract<WorkerMessageIn, { type: 'render' }>,
): Promise<void> {
  if (!layout) {
    self.postMessage({
      type: 'error',
      message: 'OpenSCAD not initialized: no render bundle mounted',
      kind: 'init-error',
    } satisfies WorkerMessageOut)
    return
  }

  const outFile = '/output.stl'
  let instance: InstanceWithEnv
  try {
    instance = await createFreshInstance(true)
  } catch (e) {
    self.postMessage({
      type: 'error',
      message: (e as Error).message || String(e),
      kind: classifyThrown(e),
    } satisfies WorkerMessageOut)
    return
  }

  try {
    self.postMessage({
      type: 'progress',
      percent: 10,
      phase: 'compiling',
      line: 'Starting OpenSCAD...',
    } satisfies WorkerMessageOut)

    const exitCode = instance.callMain(buildArgs(entryPath, params, renderMode, outFile))

    if (exitCode !== 0) {
      // OpenSCAD ran and rejected the model. The same source would be rejected
      // identically on the server, so this kind never triggers a fallback.
      self.postMessage({
        type: 'error',
        message: `OpenSCAD exited with code ${exitCode}`,
        kind: 'scad-error',
      } satisfies WorkerMessageOut)
      return
    }

    const stl = instance.FS.readFile(outFile, { encoding: 'binary' })
    self.postMessage({ type: 'result', stl } satisfies WorkerMessageOut, [stl.buffer])
  } catch (e) {
    self.postMessage({
      type: 'error',
      message: (e as Error).message || String(e),
      kind: classifyThrown(e),
    } satisfies WorkerMessageOut)
  }
}

/**
 * Time "instantiate a fresh module + render a tiny reference model".
 *
 * Both halves are measured together on purpose: instantiation dominates on a
 * healthy machine (median 42 ms vs 3 ms of geometry, measured against this
 * exact build), and it is the half that collapses on a weak one.
 */
async function handleBenchmark(): Promise<void> {
  try {
    const started = performance.now()
    const wrapper = await createOpenSCAD({
      noInitialRun: true,
      printErr: () => { /* the benchmark is a stopwatch, not a log source */ },
    } as Parameters<typeof createOpenSCAD>[0])
    const instance = wrapper.getInstance()
    instance.FS.writeFile('/benchmark.scad', BENCHMARK_SOURCE)
    const exitCode = instance.callMain(['/benchmark.scad', '-o', '/benchmark.stl'])
    const ms = performance.now() - started
    if (exitCode !== 0) {
      self.postMessage({
        type: 'error',
        message: `Benchmark render exited with code ${exitCode}`,
        kind: 'init-error',
      } satisfies WorkerMessageOut)
      return
    }
    self.postMessage({ type: 'benchmark-done', ms } satisfies WorkerMessageOut)
  } catch (e) {
    self.postMessage({
      type: 'error',
      message: (e as Error).message || String(e),
      kind: classifyThrown(e),
    } satisfies WorkerMessageOut)
  }
}

self.onmessage = (e: MessageEvent<WorkerMessageIn>) => {
  const { type } = e.data
  if (type === 'init') handleInit(e.data)
  else if (type === 'render') handleRender(e.data)
  else if (type === 'benchmark') handleBenchmark()
}
