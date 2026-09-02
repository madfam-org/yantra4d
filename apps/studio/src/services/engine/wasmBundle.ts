/**
 * The WASM render bundle: everything the browser needs to render a cartridge
 * offline, resolved server-side.
 *
 * WHY THIS REPLACES `/scad/<name>`
 * --------------------------------
 * The old worker fetched `${origin}/scad/${scad_file}` for each mode's entry
 * file and wrote it at `/<name>`. Three things were wrong with that, and each
 * one alone is fatal in production:
 *
 *   1. Nothing serves `/scad/` in production. nginx's `try_files … /index.html`
 *      answers with the app's own HTML at **200 OK**, so the worker cheerfully
 *      wrote a page of `<!doctype html>` into the virtual FS as a SCAD file.
 *   2. It fetched only the entry file. Nearly every OpenSCAD cartridge in this
 *      commons opens with `include <../../libs/BOSL2/std.scad>`; none of BOSL2
 *      was ever written to the FS, so the include could not resolve even when
 *      the entry file was real.
 *   3. No fonts were mounted, so `text()` silently rendered nothing — the base
 *      plate came out, the lettering did not.
 *
 * `GET /api/projects/<slug>/wasm-bundle` fixes all three: the server walks the
 * include/use graph transitively (allowlisted to `projects/` and `libs/`),
 * returns every file keyed by its repo-relative path, base64s the fonts, and
 * names any feature it knows the WASM build cannot execute.
 *
 * PROVEN, not assumed. Against the real `openscad-wasm@0.0.4` build under Node
 * 22 (2026-09-01): writing `libs/BOSL2/*.scad` at `/libs/BOSL2/…` and
 * `projects/gridfinity/cup.scad` at `/projects/gridfinity/cup.scad`, then
 * running the entry by that path, resolves `include <../../libs/BOSL2/std.scad>`
 * and produces a 331,951-byte STL. Mounting a TTF plus a fontconfig file and
 * pointing `FONTCONFIG_FILE` at it takes `projects/relief/plaque.scad` from a
 * 1,479-byte STL (base only, "WARNING: Can't get font") to 424,910 bytes.
 */

import { apiFetch } from '../core/apiClient'
import { getApiBase } from '../core/backendDetection'

export interface WasmBundle {
  slug: string
  engine: string
  /** Entry SCAD files, relative to the project directory (e.g. `cup.scad`). */
  entry_files: string[]
  /** Repo-relative path -> UTF-8 source, e.g. `projects/gridfinity/cup.scad`. */
  files: Record<string, string>
  /**
   * Virtual path -> base64 font bytes (`projects/<slug>/fonts/Label.ttf`,
   * `fonts/Allerta.ttf`), PLUS one special key `fonts.conf` whose value is the
   * fontconfig XML itself — text, not base64.
   */
  fonts?: Record<string, string>
  /** Features the server knows this WASM build cannot execute. */
  unsupported?: string[]
  /** Include/use targets the server could not resolve, `"<path>: <target>"`. */
  unresolved?: string[]
  bytes?: number
  etag?: string
}

export interface BundleFsLayout {
  /** Directories to create, parents before children. */
  dirs: string[]
  /** Absolute virtual paths and their UTF-8 contents. */
  files: Array<{ path: string; text: string }>
  /** Absolute virtual paths and their base64 contents. */
  fonts: Array<{ path: string; base64: string }>
  /** The fontconfig document to write at `/fonts/fonts.conf`, or null when no fonts. */
  fontsConf: string | null
  /** Absolute virtual paths of the entry files, in `entry_files` order. */
  entryPaths: string[]
}

/** The shared typeface directory in the virtual FS, mirroring `Config.FONTS_DIR`. */
export const FONT_DIR = '/fonts'
/** Where the worker writes the fontconfig document and points `FONTCONFIG_FILE`. */
export const FONTCONFIG_PATH = `${FONT_DIR}/fonts.conf`
/** fontconfig insists on a writable cache dir; without one it logs on every render. */
export const FONTCONFIG_CACHE_DIR = '/tmp/fontconfig'

/** The bundle key carrying the fontconfig XML rather than a typeface. */
const FONTS_CONF_KEY = 'fonts.conf'

/**
 * `OPENSCADPATH` for the worker: the virtual mirror of what `config.py`
 * composes for the native binary.
 *
 * Relative includes resolve against the including file's own directory and need
 * nothing set. Includes written against the search path — `include
 * <BOSL2/std.scad>`, `include <dotSCAD/src/…>` — resolve only if the worker
 * searches the same directories, in the same order, as the server did when it
 * built the bundle. A different order would let the browser render a different
 * model than the server does, from identical source.
 */
export const VIRTUAL_OPENSCADPATH = '/libs:/libs/dotSCAD/src:/projects'

/**
 * A fontconfig document, generated only when the bundle did not supply one.
 *
 * The API generates `fonts.conf` with the same `fontconfig_xml()` the native
 * renderer uses, pointed at the virtual font directories — one generator, so a
 * typeface cannot resolve on the server and fail in the browser. This local
 * version exists purely for the dev-only `/scad/` fallback, which has no API to
 * ask.
 *
 * The OpenSCAD WASM build has fontconfig and freetype compiled in but no default
 * config file: it aborts every `text()` with "Cannot load default config file:
 * No such file: (null)" until `FONTCONFIG_FILE` names one.
 */
function fallbackFontsConf(fontDirs: string[]): string {
  const dirs = fontDirs.map(d => `  <dir>${d}</dir>`).join('\n')
  return `<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
${dirs}
  <cachedir>${FONTCONFIG_CACHE_DIR}</cachedir>
</fontconfig>
`
}

/**
 * Normalise one bundle key into an absolute virtual path.
 *
 * Rejects anything that could escape the virtual root. The bundle comes from
 * our own API, but it is still remote input writing to a filesystem, and
 * `../../../etc` costs nothing to refuse.
 */
export function toVirtualPath(key: string): string | null {
  if (typeof key !== 'string' || key.length === 0) return null
  const trimmed = key.replace(/^\/+/, '')
  if (!trimmed) return null
  const segments = trimmed.split('/')
  for (const segment of segments) {
    if (segment === '' || segment === '.' || segment === '..') return null
  }
  return `/${segments.join('/')}`
}

/** Every ancestor directory of an absolute path, shallowest first. */
function ancestorDirs(absolutePath: string): string[] {
  const segments = absolutePath.split('/').filter(Boolean)
  segments.pop() // drop the file name
  const dirs: string[] = []
  let current = ''
  for (const segment of segments) {
    current += `/${segment}`
    dirs.push(current)
  }
  return dirs
}

/**
 * Turn a bundle into the exact sequence of FS operations the worker performs.
 *
 * PURE — no WASM, no network, no globals. This is where the include-resolution
 * contract lives (`projects/<slug>/x.scad` and `libs/BOSL2/std.scad` land at
 * paths whose relative distance is what `include <../../libs/BOSL2/std.scad>`
 * expects), so it is worth pinning in a unit test rather than discovering in a
 * browser.
 */
export function planBundleFsLayout(bundle: WasmBundle): BundleFsLayout {
  const dirSet = new Set<string>()
  const files: BundleFsLayout['files'] = []

  const addDirs = (absolutePath: string) => {
    for (const dir of ancestorDirs(absolutePath)) dirSet.add(dir)
  }

  for (const [key, text] of Object.entries(bundle.files ?? {})) {
    const path = toVirtualPath(key)
    if (!path || typeof text !== 'string') continue
    addDirs(path)
    files.push({ path, text })
  }

  const fonts: BundleFsLayout['fonts'] = []
  const fontDirs = new Set<string>()
  let suppliedFontsConf: string | null = null

  for (const [key, value] of Object.entries(bundle.fonts ?? {})) {
    if (typeof value !== 'string') continue
    // The one key that is not a typeface. Its value is fontconfig XML, already
    // pointed at the virtual directories below, so it is written verbatim
    // rather than regenerated.
    if (key === FONTS_CONF_KEY) {
      suppliedFontsConf = value
      continue
    }
    // Fonts keep the virtual path the bundle gave them — `fonts.conf` names
    // those exact directories, so flattening them into /fonts would silently
    // unmount every cartridge-local typeface.
    const fontPath = toVirtualPath(key)
    if (!fontPath) continue
    addDirs(fontPath)
    fontDirs.add(fontPath.slice(0, fontPath.lastIndexOf('/')) || '/')
    fonts.push({ path: fontPath, base64: value })
  }

  const hasFonts = fonts.length > 0
  if (hasFonts) {
    for (const dir of fontDirs) dirSet.add(dir)
    dirSet.add(FONT_DIR) // FONTCONFIG_PATH lives here even when no shared font does
    for (const dir of ancestorDirs(`${FONTCONFIG_CACHE_DIR}/x`)) dirSet.add(dir)
  }

  // Parents before children: `FS.mkdir` does not create intermediates.
  const dirs = [...dirSet].sort((a, b) => a.split('/').length - b.split('/').length || a.localeCompare(b))

  const projectDir = `/projects/${bundle.slug}`
  const entryPaths: string[] = []
  for (const entry of bundle.entry_files ?? []) {
    if (typeof entry !== 'string' || !entry) continue
    // An entry may arrive project-relative (`cup.scad`, the contract) or already
    // repo-relative (`projects/gridfinity/cup.scad`). Accept both; the file map
    // is the authority on which one actually exists.
    const asRepoRelative = toVirtualPath(entry)
    const asProjectRelative = toVirtualPath(`${projectDir}/${entry}`)
    const known = new Set(files.map(f => f.path))
    if (asProjectRelative && known.has(asProjectRelative)) entryPaths.push(asProjectRelative)
    else if (asRepoRelative && known.has(asRepoRelative)) entryPaths.push(asRepoRelative)
    else if (asProjectRelative) entryPaths.push(asProjectRelative)
  }

  return {
    dirs,
    files,
    fonts,
    fontsConf: hasFonts ? (suppliedFontsConf ?? fallbackFontsConf([...fontDirs])) : null,
    entryPaths,
  }
}

/**
 * Resolve one mode's `scad_file` to its absolute path inside the bundle.
 * PURE. Falls back to the project directory so an entry the bundle did not
 * enumerate still produces a sensible path (and a legible OpenSCAD error).
 */
export function resolveEntryPath(bundle: WasmBundle, scadFile: string): string {
  const projectDir = `/projects/${bundle.slug}`
  const candidates = [
    toVirtualPath(`${projectDir}/${scadFile}`),
    toVirtualPath(scadFile),
  ].filter((p): p is string => p !== null)
  const known = new Set(Object.keys(bundle.files ?? {}).map(toVirtualPath))
  for (const candidate of candidates) {
    if (known.has(candidate)) return candidate
  }
  return candidates[0] ?? `${projectDir}/${scadFile}`
}

// ── Fetching ────────────────────────────────────────────────────────────────

export class BundleUnavailableError extends Error {
  readonly status: number
  readonly code: string
  constructor(message: string, status: number, code: string) {
    super(message)
    this.name = 'BundleUnavailableError'
    this.status = status
    this.code = code
  }
}

/** One bundle per slug, keyed by etag so a republished cartridge is refetched. */
const _bundleCache = new Map<string, WasmBundle>()
const _inFlight = new Map<string, Promise<WasmBundle>>()

export function clearBundleCache(slug?: string): void {
  if (slug) {
    _bundleCache.delete(slug)
    _inFlight.delete(slug)
  } else {
    _bundleCache.clear()
    _inFlight.clear()
  }
}

/** The cached bundle for a slug, if one has been fetched. Never fetches. */
export function peekBundle(slug: string): WasmBundle | null {
  return _bundleCache.get(slug) ?? null
}

function isBundleShape(value: unknown): value is WasmBundle {
  if (!value || typeof value !== 'object') return false
  const b = value as Partial<WasmBundle>
  return typeof b.slug === 'string'
    && typeof b.files === 'object' && b.files !== null
    && Array.isArray(b.entry_files)
}

/**
 * Fetch (and memoise) the bundle for a slug.
 *
 * Goes through `apiFetch` so the bearer token rides along: a private project
 * answers 403 `project_locked` to an anonymous caller, and that must surface as
 * a locked project rather than as "your browser can't render this".
 */
export async function fetchWasmBundle(
  slug: string,
  { signal, manifest }: { signal?: AbortSignal; manifest?: LegacyFallbackManifest } = {},
): Promise<WasmBundle> {
  const cached = _bundleCache.get(slug)
  if (cached) return cached

  const existing = _inFlight.get(slug)
  if (existing) return existing

  const request = (async () => {
    const url = `${getApiBase()}/api/projects/${encodeURIComponent(slug)}/wasm-bundle`
    let response: Response
    try {
      response = await apiFetch(url, { signal })
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') throw err
      const fallback = await legacyScadFallback(slug, manifest)
      if (fallback) return fallback
      throw new BundleUnavailableError(
        `Could not reach the render bundle for "${slug}": ${(err as Error).message}`,
        0,
        'network_error',
      )
    }

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new BundleUnavailableError(
          `Render bundle for "${slug}" is not accessible (HTTP ${response.status})`,
          response.status,
          'project_locked',
        )
      }
      const fallback = await legacyScadFallback(slug, manifest)
      if (fallback) return fallback
      throw new BundleUnavailableError(
        `Render bundle for "${slug}" unavailable (HTTP ${response.status})`,
        response.status,
        'bundle_unavailable',
      )
    }

    const body: unknown = await response.json()
    if (!isBundleShape(body)) {
      throw new BundleUnavailableError(
        `Render bundle for "${slug}" is malformed`,
        response.status,
        'bundle_malformed',
      )
    }
    const bundle: WasmBundle = { ...body, slug: body.slug || slug }
    _bundleCache.set(slug, bundle)
    return bundle
  })().finally(() => { _inFlight.delete(slug) })

  _inFlight.set(slug, request)
  return request
}

interface LegacyFallbackManifest {
  modes?: Array<{ scad_file?: string }>
}

/**
 * DEV-ONLY FALLBACK — the pre-bundle `/scad/<name>` path, kept behind the same
 * interface so a developer running `vite dev` against a backend that predates
 * `/api/projects/<slug>/wasm-bundle` still gets a render.
 *
 * It is deliberately unavailable in a production build. In production this path
 * is the bug the bundle exists to fix: nginx answers `/scad/anything` with the
 * SPA's own `index.html` at 200 OK, so the "SCAD source" written to the virtual
 * FS is a page of HTML. Better to fail with `bundle_unavailable` and fall back
 * to the server than to render nothing and blame the visitor's machine.
 *
 * It also cannot resolve `include <../../libs/BOSL2/…>` or mount fonts, so it
 * only ever worked for the handful of self-contained cartridges.
 */
async function legacyScadFallback(
  slug: string,
  manifest?: LegacyFallbackManifest,
): Promise<WasmBundle | null> {
  if (!import.meta.env?.DEV) return null
  if (!manifest?.modes?.length) return null

  const names = [...new Set(manifest.modes.map(m => m.scad_file).filter((n): n is string => !!n))]
  if (names.length === 0) return null

  const baseUrl = (import.meta.env?.BASE_URL as string | undefined) || '/'
  const files: Record<string, string> = {}
  for (const name of names) {
    try {
      const res = await fetch(`${baseUrl.replace(/\/$/, '')}/scad/${name}`)
      if (!res.ok) return null
      const text = await res.text()
      // The 200-OK-HTML trap, caught explicitly rather than written to the FS.
      if (/^\s*<(!doctype|html)/i.test(text)) return null
      files[`projects/${slug}/${name}`] = text
    } catch {
      return null
    }
  }

  console.warn(
    `[wasm-bundle] DEV FALLBACK: served "${slug}" from /scad/. No libraries and no fonts — `
    + 'cartridges that include BOSL2 or call text() will not render correctly. '
    + 'Bring up GET /api/projects/<slug>/wasm-bundle for the real thing.',
  )
  const bundle: WasmBundle = {
    slug,
    engine: 'openscad',
    entry_files: names,
    files,
    unsupported: [],
  }
  _bundleCache.set(slug, bundle)
  return bundle
}
