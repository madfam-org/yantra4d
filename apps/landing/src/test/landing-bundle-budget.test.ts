/**
 * Tests for `scripts/ci/landing-bundle-budget.mjs`, the transfer-size gate the
 * landing CI job runs on every build.
 *
 * The gate's three rules are exercised against throwaway fixture dists built in
 * a temp dir, so the assertions do not move when the real bundle changes:
 *
 *   1. `initial` is REACHABILITY — every script the two entry pages request at
 *      load plus the static import closure — and a dynamic `import()` is not an
 *      edge;
 *   2. a 3D chunk that is statically reachable is initial (so it fails the
 *      initial budget like any load-time script) and is called out as a
 *      warning naming its importer, on top of the size check by name; and
 *   3. every number comes from the budgets file — a missing key is an error,
 *      never a default.
 *
 * One test reads the committed `perf-budgets.json`: it is the regression guard
 * that the gate can still read the real file.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {
  EXIT_BREACH,
  EXIT_OK,
  EXIT_USAGE,
  ENTRY_PAGES,
  analyzeDist,
  compressedSizes,
  fileStem,
  formatMarkdown,
  htmlEntrypoints,
  jsImports,
  readBudgets,
  resolveLocal,
  run,
} from '../../../../scripts/ci/landing-bundle-budget.mjs'

// ─── Fixture dist builder ───────────────────────────────────────────────────

type Budgets = { initialJsBytes: number; threeChunkBytes: number; postprocessingChunkBytes: number }

type DistSpec = {
  /** `_astro/<name>` → module source. */
  chunks?: Record<string, string>
  /** Override the default `index.html`. */
  index?: string
  /** Override the default `en/index.html`; `null` omits the page. */
  en?: string | null
}

/** Padding that compresses like real code: varied, but not random. */
function pad(seed: string, lines = 40): string {
  return Array.from({ length: lines }, (_, i) => `function ${seed}${i}(a,b){return a*${i}+b-${seed.length}}`).join('\n')
}

const RUNTIME = 'rolldown-runtime.BBBBBBBB.js'
const CLIENT = 'client.AAAAAAAA.js'
const ISLAND = 'Island.CCCCCCCC.js'
const SIDE = 'side-effect.DDDDDDDD.js'
const REEXPORT = 'reexport.EEEEEEEE.js'
const THREE = 'vendor-three.FFFFFFFF.js'
const POST = 'vendor-postprocessing.GGGGGGGG.js'
const ORPHAN = 'orphan.HHHHHHHH.js'
const PRELOADED = 'preloaded.IIIIIIII.js'
const HOISTED = 'hoisted.JJJJJJJJ.js'
const EN_ONLY = 'EnOnly.KKKKKKKK.js'

/** The default chunk set: what a healthy Phase 2 build looks like. */
function healthyChunks(): Record<string, string> {
  return {
    [RUNTIME]: `export var r=1;\n${pad('rt')}`,
    [CLIENT]: `import{r as e}from"./${RUNTIME}";export{e as default};\n${pad('cl')}`,
    [ISLAND]:
      `import{r as e}from"./${RUNTIME}";import"./${SIDE}";export*from"./${REEXPORT}";` +
      `const t=()=>import("./${THREE}");const s="import x from './not-a-file.js'";export default t;\n${pad('is')}`,
    [SIDE]: `console.log("side");\n${pad('se')}`,
    [REEXPORT]: `export const q=2;\n${pad('re')}`,
    [THREE]: `import{r as e}from"./${RUNTIME}";const p=()=>import("./${POST}");export{p};\n${pad('three', 400)}`,
    [POST]: `export const bloom=1;\n${pad('post', 80)}`,
    [ORPHAN]: `export const nobody=1;\n${pad('or')}`,
    [PRELOADED]: `export const pre=1;\n${pad('pr')}`,
    [HOISTED]: `document.title="x";\n${pad('ho')}`,
    [EN_ONLY]: `import{r as e}from"./${RUNTIME}";export default e;\n${pad('en')}`,
  }
}

const INDEX_HTML = `<!doctype html><html lang="es" data-tier="still"><head>
<script>(function(){document.documentElement.setAttribute("data-tier","still")})()</script>
<link rel="stylesheet" href="/_astro/i18n.CSSCSSCS.css">
<link href="/_astro/${PRELOADED}" rel="modulepreload">
<script type="module" src="/_astro/${HOISTED}"></script>
<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{"token":"x"}'></script>
</head><body>
<astro-island uid="Z1" component-url="/_astro/${ISLAND}" component-export="default" renderer-url="/_astro/${CLIENT}" props="{}" ssr client="only" opts="{}"></astro-island>
</body></html>`

const EN_HTML = `<!doctype html><html lang="en" data-tier="still"><head></head><body>
<astro-island uid="Z2" component-url="/_astro/${EN_ONLY}" component-export="default" renderer-url="/_astro/${CLIENT}" props="{}" ssr client="load" opts="{}"></astro-island>
</body></html>`

let dirs: string[] = []

function makeDist(spec: DistSpec = {}): string {
  const dist = fs.mkdtempSync(path.join(os.tmpdir(), 'y4d-budget-'))
  dirs.push(dist)
  fs.mkdirSync(path.join(dist, '_astro'), { recursive: true })
  for (const [name, source] of Object.entries(spec.chunks ?? healthyChunks())) {
    fs.writeFileSync(path.join(dist, '_astro', name), source)
  }
  fs.writeFileSync(path.join(dist, 'index.html'), spec.index ?? INDEX_HTML)
  if (spec.en !== null) {
    fs.mkdirSync(path.join(dist, 'en'), { recursive: true })
    fs.writeFileSync(path.join(dist, 'en', 'index.html'), spec.en ?? EN_HTML)
  }
  return dist
}

/** A budgets file in the shape of perf-budgets.json (only `transfer` matters to the gate). */
function makeBudgetsFile(transfer: Partial<Budgets> | Record<string, unknown>): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'y4d-budgets-'))
  dirs.push(dir)
  const file = path.join(dir, 'perf-budgets.json')
  fs.writeFileSync(file, JSON.stringify({ version: 1, transfer }, null, 2))
  return file
}

const GENEROUS: Budgets = { initialJsBytes: 10 * 1024 * 1024, threeChunkBytes: 10 * 1024 * 1024, postprocessingChunkBytes: 10 * 1024 * 1024 }

function brotliOf(source: string): number {
  return compressedSizes(Buffer.from(source)).brotli
}

function classes(dist: string, budgets: Budgets = GENEROUS): Record<string, string> {
  return Object.fromEntries(analyzeDist(dist, budgets).files.map((f) => [path.basename(f.file), f.class]))
}

/** Collect stdout/stderr from a `run()` call instead of printing it. */
function capture() {
  const out: string[] = []
  const err: string[] = []
  return {
    out,
    err,
    log: (m: unknown) => out.push(String(m)),
    logError: (m: unknown) => err.push(String(m)),
  }
}

beforeEach(() => {
  dirs = []
})

afterEach(() => {
  for (const d of dirs) fs.rmSync(d, { recursive: true, force: true })
  dirs = []
})

// ─── Parsing ────────────────────────────────────────────────────────────────

describe('htmlEntrypoints', () => {
  it('finds script src, modulepreload (any attribute order) and both island urls', () => {
    const found = htmlEntrypoints(INDEX_HTML)
    expect(found.map((f) => f.url)).toEqual([
      `/_astro/${PRELOADED}`,
      `/_astro/${HOISTED}`,
      'https://static.cloudflareinsights.com/beacon.min.js',
      `/_astro/${ISLAND}`,
      `/_astro/${CLIENT}`,
    ])
  })

  it('ignores inline scripts and stylesheets, and records the island directive', () => {
    const found = htmlEntrypoints(INDEX_HTML)
    expect(found.some((f) => f.url.endsWith('.css'))).toBe(false)
    expect(found.find((f) => f.url.endsWith(ISLAND))?.via).toBe('island component (client:only)')
    expect(found.find((f) => f.url.endsWith(CLIENT))?.via).toBe('island renderer (client:only)')
    expect(htmlEntrypoints(EN_HTML).find((f) => f.url.endsWith(EN_ONLY))?.via).toBe('island component (client:load)')
  })
})

describe('resolveLocal', () => {
  const dist = '/dist'
  const page = '/dist/index.html'

  it('maps absolute and relative JS urls into dist', () => {
    expect(resolveLocal(dist, page, '/_astro/a.js')).toBe('/dist/_astro/a.js')
    expect(resolveLocal(dist, '/dist/_astro/a.js', './b.js')).toBe('/dist/_astro/b.js')
    expect(resolveLocal(dist, page, '/_astro/a.js?v=1')).toBe('/dist/_astro/a.js')
  })

  it('refuses external urls, non-JS files and anything that escapes dist', () => {
    expect(resolveLocal(dist, page, 'https://static.cloudflareinsights.com/beacon.min.js')).toBeNull()
    expect(resolveLocal(dist, page, '//cdn.example/x.js')).toBeNull()
    expect(resolveLocal(dist, page, '/_astro/i18n.css')).toBeNull()
    expect(resolveLocal(dist, '/dist/_astro/a.js', '../../etc/evil.js')).toBeNull()
  })
})

describe('jsImports', () => {
  it('reads minified static imports and re-exports, and keeps dynamic imports apart', () => {
    const src =
      'import{f as t,p as n}from"./vendor-three.X.js";import{r as e}from\'./rt.js\';' +
      'import"./side.js";export*from"./re.js";export{a as b}from"./named.js";' +
      'const l=()=>import("./lazy.js");const m=import.meta.url;'
    expect(jsImports(src)).toEqual({
      static: ['./vendor-three.X.js', './rt.js', './re.js', './named.js', './side.js'],
      dynamic: ['./lazy.js'],
    })
  })

  it('ignores bare specifiers, urls and the word import inside a string', () => {
    const src = 'import React from"react";import"https://cdn/x.js";const s="import x from \'./y.js\'";'
    // The string literal IS matched by the pattern — it is indistinguishable
    // from code — and is then dropped by the caller because no such file exists.
    // What must never come back is a bare package or a URL.
    const { static: statics } = jsImports(src)
    expect(statics).not.toContain('react')
    expect(statics).not.toContain('https://cdn/x.js')
  })

  it('does not mistake export default or export const for a re-export', () => {
    expect(jsImports('export default function x(){}export const y=1;import{z}from"./z.js"')).toEqual({
      static: ['./z.js'],
      dynamic: [],
    })
  })
})

describe('fileStem', () => {
  it('drops the 8-character hash Astro appends', () => {
    expect(fileStem('_astro/ProjectGalleryContainer.BdGhvEbY.js')).toBe('ProjectGalleryContainer')
    expect(fileStem('_astro/client.Bd--AgZM.js')).toBe('client')
    expect(fileStem('_astro/plain.js')).toBe('plain')
  })
})

describe('compressedSizes', () => {
  it('returns raw, gzip and brotli, in that order of size for code-like text', () => {
    const sizes = compressedSizes(Buffer.from(pad('z', 200)))
    expect(sizes.raw).toBeGreaterThan(sizes.gzip)
    expect(sizes.gzip).toBeGreaterThan(sizes.brotli)
    expect(sizes.brotli).toBeGreaterThan(0)
  })
})

// ─── Classification ─────────────────────────────────────────────────────────

describe('analyzeDist — classification', () => {
  it('marks the load-time graph of both pages initial, and the rest by name', () => {
    expect(classes(makeDist())).toEqual({
      [RUNTIME]: 'initial',
      [CLIENT]: 'initial',
      [ISLAND]: 'initial',
      [SIDE]: 'initial', // bare `import "./x"`
      [REEXPORT]: 'initial', // `export * from`
      [PRELOADED]: 'initial', // <link rel="modulepreload">
      [HOISTED]: 'initial', // <script src>
      [EN_ONLY]: 'initial', // only en/index.html references it
      [THREE]: 'three', // reached by dynamic import() only
      [POST]: 'post',
      [ORPHAN]: 'other',
    })
  })

  it('records where each initial file came from and what it imports lazily', () => {
    const report = analyzeDist(makeDist(), GENEROUS)
    const island = report.files.find((f) => f.file.endsWith(ISLAND))!
    expect(island.via).toEqual(['index.html: island component (client:only)'])
    expect(island.dynamicImports).toEqual([`_astro/${THREE}`])
    const runtime = report.files.find((f) => f.file.endsWith(RUNTIME))!
    expect(runtime.importers).toEqual(expect.arrayContaining([`_astro/${CLIENT}`, `_astro/${ISLAND}`, `_astro/${EN_ONLY}`]))
    // The 3D chunk is not reachable, so its own imports are not walked into `initial`.
    const three = report.files.find((f) => f.file.endsWith(THREE))!
    expect(three.initial).toBe(false)
    expect(three.importers).toEqual([])
  })

  it('does not count a string that merely looks like an import', () => {
    // `Island` carries `"import x from './not-a-file.js'"` inside a string literal.
    const report = analyzeDist(makeDist(), GENEROUS)
    expect(report.unresolved).toEqual([])
    expect(report.files.some((f) => f.file.includes('not-a-file'))).toBe(false)
  })
})

describe('analyzeDist — totals', () => {
  it('sums brotli per class and by chunk name', () => {
    const chunks = healthyChunks()
    const report = analyzeDist(makeDist({ chunks }), GENEROUS)
    const initialNames = [RUNTIME, CLIENT, ISLAND, SIDE, REEXPORT, PRELOADED, HOISTED, EN_ONLY]
    const expectedInitial = initialNames.reduce((sum, n) => sum + brotliOf(chunks[n]), 0)
    expect(report.totals.initial.brotli).toBe(expectedInitial)
    expect(report.totals.initial.files).toBe(initialNames.length)
    expect(report.chunks.three.brotli).toBe(brotliOf(chunks[THREE]))
    expect(report.chunks.post.brotli).toBe(brotliOf(chunks[POST]))
    expect(report.totals.other.brotli).toBe(brotliOf(chunks[ORPHAN]))
    expect(report.totals.all.files).toBe(Object.keys(chunks).length)
    expect(report.totals.all.brotli).toBe(Object.values(chunks).reduce((s, c) => s + brotliOf(c), 0))
  })

  it('lists files largest first', () => {
    const report = analyzeDist(makeDist(), GENEROUS)
    const sizes = report.files.map((f) => f.brotli)
    expect(sizes).toEqual([...sizes].sort((a, b) => b - a))
    expect(report.files[0].file).toBe(`_astro/${THREE}`)
  })
})

// ─── Budgets ────────────────────────────────────────────────────────────────

describe('analyzeDist — budgets', () => {
  it('holds when every total fits', () => {
    const report = analyzeDist(makeDist(), GENEROUS)
    expect(report.ok).toBe(true)
    expect(report.breaches).toEqual([])
    expect(report.checks.map((c) => [c.id, c.ok])).toEqual([
      ['initial', true],
      ['three', true],
      ['post', true],
    ])
  })

  it('breaches the initial budget by one byte, and says by how much', () => {
    const healthy = analyzeDist(makeDist(), GENEROUS)
    const budgets = { ...GENEROUS, initialJsBytes: healthy.totals.initial.brotli - 1 }
    const report = analyzeDist(makeDist(), budgets)
    expect(report.ok).toBe(false)
    expect(report.breaches.map((b) => b.kind)).toEqual(['over-budget:initial'])
    expect(report.breaches[0].message).toContain('transfer.initialJsBytes')
    expect(report.breaches[0].message).toContain(String(budgets.initialJsBytes))
  })

  it('checks the 3D and post-processing chunks by name even though they are not initial', () => {
    const healthy = analyzeDist(makeDist(), GENEROUS)
    const report = analyzeDist(makeDist(), {
      ...GENEROUS,
      threeChunkBytes: healthy.chunks.three.brotli - 1,
      postprocessingChunkBytes: healthy.chunks.post.brotli - 1,
    })
    expect(report.breaches.map((b) => b.kind).sort()).toEqual(['over-budget:post', 'over-budget:three'])
  })

  it('treats a statically imported 3D chunk as initial, and warns naming the importer', () => {
    const chunks = healthyChunks()
    chunks[ISLAND] = `import{r as e}from"./${RUNTIME}";import{p}from"./${THREE}";export default p;\n${pad('is')}`
    const dist = makeDist({ chunks })
    const report = analyzeDist(dist, GENEROUS)

    expect(classes(dist)[THREE]).toBe('initial')
    expect(report.totals.initial.brotli).toBeGreaterThanOrEqual(brotliOf(chunks[THREE]))
    // The by-name check still sees the chunk, so an oversize one is caught too.
    expect(report.chunks.three.brotli).toBe(brotliOf(chunks[THREE]))
    // Generous budgets hold, so the wiring is a warning, not a breach: the
    // budget NUMBER is the gate, and with a real budget the chunk's bytes in
    // the initial total are what fail it.
    expect(report.breaches).toEqual([])
    expect(report.ok).toBe(true)
    expect(report.warnings.map((w) => w.kind)).toEqual(['static-3d'])
    expect(report.warnings[0].message).toContain(`_astro/${ISLAND}`)
    expect(report.warnings[0].message).toContain('dynamic import()')
    expect(report.files.find((f) => f.file.endsWith(THREE))!.note).toContain('3D chunk in the initial graph')

    // With a real-sized initial budget the same dist fails on the total.
    const tight = analyzeDist(dist, { ...GENEROUS, initialJsBytes: brotliOf(chunks[THREE]) })
    expect(tight.breaches.map((b) => b.kind)).toEqual(['over-budget:initial'])
  })

  it('warns about a 3D chunk wired straight from the page markup too', () => {
    const index = INDEX_HTML.replace(`<script type="module" src="/_astro/${HOISTED}"></script>`, `<script type="module" src="/_astro/${THREE}"></script>`)
    const report = analyzeDist(makeDist({ index }), GENEROUS)
    expect(report.warnings.map((w) => w.kind)).toEqual(['static-3d'])
    expect(report.warnings[0].message).toContain('index.html: <script src>')
  })
})

// ─── Budgets file ───────────────────────────────────────────────────────────

describe('readBudgets', () => {
  it('reads the three transfer budgets', () => {
    const file = makeBudgetsFile({ initialJsBytes: 100, threeChunkBytes: 200, postprocessingChunkBytes: 300 })
    expect(readBudgets(file)).toEqual({ initialJsBytes: 100, threeChunkBytes: 200, postprocessingChunkBytes: 300 })
  })

  it('refuses a missing or non-positive key instead of defaulting it', () => {
    expect(() => readBudgets(makeBudgetsFile({ initialJsBytes: 100, threeChunkBytes: 200 }))).toThrow(/postprocessingChunkBytes/)
    expect(() => readBudgets(makeBudgetsFile({ initialJsBytes: 0, threeChunkBytes: 200, postprocessingChunkBytes: 300 }))).toThrow(/initialJsBytes/)
    expect(() => readBudgets(makeBudgetsFile({ initialJsBytes: '40k', threeChunkBytes: 200, postprocessingChunkBytes: 300 }))).toThrow(/initialJsBytes/)
  })

  it('reads the committed perf-budgets.json (the file the gate really runs against)', () => {
    const budgets = readBudgets(path.resolve(__dirname, '..', '..', 'perf-budgets.json'))
    for (const value of Object.values(budgets)) expect(value).toBeGreaterThan(0)
    expect(budgets.initialJsBytes).toBeLessThan(budgets.threeChunkBytes)
  })
})

// ─── CLI ────────────────────────────────────────────────────────────────────

describe('run', () => {
  const generousFile = () => makeBudgetsFile(GENEROUS)

  it('exits 0 and prints the report when the budgets hold', () => {
    const io = capture()
    expect(run({ argv: [makeDist(), '--budgets', generousFile()], env: {}, ...io })).toBe(EXIT_OK)
    const out = io.out.join('\n')
    expect(out).toContain('### Landing bundle budget')
    expect(out).toContain('| file | gzip | brotli | class | note |')
    expect(out).toContain('All budgets hold.')
    expect(io.err).toEqual([])
  })

  it('exits 1 with an ::error:: line per breach', () => {
    const budgets = makeBudgetsFile({ ...GENEROUS, initialJsBytes: 1 })
    const io = capture()
    expect(run({ argv: [makeDist(), '--budgets', budgets], env: {}, ...io })).toBe(EXIT_BREACH)
    expect(io.err.filter((l) => l.startsWith('::error::'))).toHaveLength(1)
    expect(io.err[0]).toContain('initial JS (reachable at load)')
    expect(io.out.join('\n')).toContain('**OVER**')
  })

  it('exits 0 but prints a ::warning:: when the 3D chunk is wired statically under a generous budget', () => {
    const chunks = healthyChunks()
    chunks[ISLAND] = `import{r as e}from"./${RUNTIME}";import{p}from"./${THREE}";export default p;\n${pad('is')}`
    const io = capture()
    expect(run({ argv: [makeDist({ chunks }), '--budgets', generousFile()], env: {}, ...io })).toBe(EXIT_OK)
    expect(io.err.filter((l) => l.startsWith('::warning::'))).toHaveLength(1)
    expect(io.err.filter((l) => l.startsWith('::error::'))).toHaveLength(0)
    expect(io.out.join('\n')).toContain('**1 warning(s):**')
  })

  it('exits 2 when there is nothing to measure, and says what to do', () => {
    const io = capture()
    expect(run({ argv: [path.join(os.tmpdir(), 'y4d-no-such-dist'), '--budgets', generousFile()], env: {}, ...io })).toBe(EXIT_USAGE)
    expect(io.err.join('\n')).toContain('npm run build')

    const noEn = capture()
    expect(run({ argv: [makeDist({ en: null }), '--budgets', generousFile()], env: {}, ...noEn })).toBe(EXIT_USAGE)
    expect(noEn.err.join('\n')).toContain(ENTRY_PAGES[1])

    const badBudgets = capture()
    expect(run({ argv: [makeDist(), '--budgets', makeBudgetsFile({})], env: {}, ...badBudgets })).toBe(EXIT_USAGE)
    expect(badBudgets.err.join('\n')).toContain('transfer.initialJsBytes')

    const badFlag = capture()
    expect(run({ argv: [makeDist(), '--nope'], env: {}, ...badFlag })).toBe(EXIT_USAGE)
  })

  it('writes --json and appends the report to GITHUB_STEP_SUMMARY', () => {
    const dist = makeDist()
    const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'y4d-out-'))
    dirs.push(outDir)
    const jsonPath = path.join(outDir, 'nested', 'budget.json')
    const summary = path.join(outDir, 'summary.md')
    fs.writeFileSync(summary, 'previous step\n')

    const io = capture()
    expect(run({ argv: [dist, '--budgets', generousFile(), '--json', jsonPath], env: { GITHUB_STEP_SUMMARY: summary }, ...io })).toBe(EXIT_OK)

    const json = JSON.parse(fs.readFileSync(jsonPath, 'utf8'))
    expect(json.ok).toBe(true)
    expect(json.checks.map((c: { id: string }) => c.id)).toEqual(['initial', 'three', 'post'])
    expect(json.files.map((f: { file: string }) => f.file)).toContain(`_astro/${THREE}`)
    expect(json.budgets).toEqual(GENEROUS)

    const written = fs.readFileSync(summary, 'utf8')
    expect(written.startsWith('previous step\n')).toBe(true)
    expect(written).toContain('### Landing bundle budget')
  })

  it('prints deltas against a --baseline, matching files across hashes', () => {
    const before = makeDist()
    const baselinePath = path.join(before, 'baseline.json')
    expect(run({ argv: [before, '--budgets', generousFile(), '--json', baselinePath], env: {}, ...capture() })).toBe(EXIT_OK)

    // Same stems, new hashes, a bigger island, and one chunk gone.
    const chunks = healthyChunks()
    chunks['Island.NEWHASH1.js'] = `${chunks[ISLAND]}\n${pad('grow', 60)}`
    delete chunks[ISLAND]
    delete chunks[ORPHAN]
    const index = INDEX_HTML.replace(ISLAND, 'Island.NEWHASH1.js')
    const after = makeDist({ chunks, index })

    const io = capture()
    expect(run({ argv: [after, '--budgets', generousFile(), '--baseline', baselinePath], env: {}, ...io })).toBe(EXIT_OK)
    const out = io.out.join('\n')
    expect(out).toContain('Δ brotli')
    const islandRow = out.split('\n').find((l) => l.includes('Island.NEWHASH1.js'))!
    expect(islandRow).toMatch(/\| \+[\d.]+ (KB|B) \|/)
    expect(out).toContain('removed since baseline')
    expect(out).toContain('orphan')
  })

  it('keeps going without deltas when the baseline is unreadable', () => {
    const io = capture()
    expect(run({ argv: [makeDist(), '--budgets', generousFile(), '--baseline', '/no/such/baseline.json'], env: {}, ...io })).toBe(EXIT_OK)
    expect(io.err.join('\n')).toContain('baseline')
    expect(io.out.join('\n')).not.toContain('Δ brotli')
  })
})

describe('formatMarkdown', () => {
  it('shows the class breakdown and the breach list', () => {
    const report = analyzeDist(makeDist(), { ...GENEROUS, initialJsBytes: 1 })
    const md = formatMarkdown(report)
    expect(md).toContain('By class (brotli): initial 8 file(s)')
    expect(md).toContain('**1 breach(es):**')
    expect(md).toContain('| initial JS (reachable at load) |')
  })
})
