/**
 * Prerendered default previews: the landing's model pipeline renders every
 * public cartridge at its default mode and default parameters, then publishes
 * meshopt-compressed GLBs plus `manifest.json` under `yantra4d.com/models/`
 * (`.github/workflows/prerender-commons.yml`, guide:
 * `docs/guides/landing-models-pipeline.md`).
 *
 * The Studio shows that mesh on project open, before anything has rendered, so
 * a visitor whose tier cannot run the cartridge's engine still sees the object
 * instead of an empty stage. It is a picture of the DEFAULT configuration at
 * the manifest's commons pin, labelled as such — never a render result.
 *
 * Every failure here is silent by design: no manifest, a malformed one, a slug
 * it does not list, a network error. The caller gets `null` and shows nothing.
 */

/**
 * The viewer's geometry key for the preview. It frames the camera like any
 * part, but it is not a render result, so it never reaches `onGeometryStats`
 * (print estimates, model info).
 */
export const PRERENDERED_PREVIEW_PART = '__prerendered_preview__'

/** Where the landing serves the models when the Studio is on another origin. */
export const REMOTE_MODELS_BASE = 'https://yantra4d.com/models/'

/** Hosts that serve the landing build, and therefore `/models/`, themselves. */
const LANDING_HOSTS: ReadonlySet<string> = new Set(['yantra4d.com', 'www.yantra4d.com'])

/** The manifest is regenerated monthly; an hour in memory is plenty. */
export const MANIFEST_TTL_MS = 60 * 60 * 1000
/** A failed fetch is retried sooner, but not on every project open. */
export const MANIFEST_FAILURE_TTL_MS = 5 * 60 * 1000

export interface PrerenderFile {
  file: string
  bytes?: number
  triangles?: number
}

export interface PrerenderEntry {
  slug: string
  lod0?: PrerenderFile
  lod1?: PrerenderFile
}

export interface PrerenderManifest {
  version?: number
  generated?: string
  source?: { kind?: string; commons_pin?: string }
  models: PrerenderEntry[]
}

export type PrerenderLod = 'lod0' | 'lod1'

export interface PrerenderCandidate {
  url: string
  lod: PrerenderLod
}

export interface PrerenderedPreviewInfo {
  slug: string
  /** Best first: lod0 (≤ 60 KiB) when the manifest has it, then lod1 (≤ 12 KiB). */
  candidates: PrerenderCandidate[]
  /** The commons commit the meshes were rendered from, when the manifest says. */
  commonsPin: string | null
  /** When the manifest was generated (ISO 8601), when it says. */
  generated: string | null
}

/**
 * The base URL for `/models/`, with a trailing slash.
 *
 * `VITE_PRERENDER_MODELS_BASE` wins when set (a self-hosted landing, a local
 * dev server). Otherwise the landing's own hosts read their files same-origin,
 * and every other origin (app.yantra4d.com, localhost) reads the landing's,
 * which answers with CORS for those origins (apps/landing/nginx.conf).
 */
export function resolveModelsBase(
  env: Record<string, unknown> = import.meta.env as Record<string, unknown>,
  location: Pick<Location, 'hostname'> | null = typeof window !== 'undefined' ? window.location : null,
): string {
  const override = typeof env?.VITE_PRERENDER_MODELS_BASE === 'string' ? env.VITE_PRERENDER_MODELS_BASE.trim() : ''
  if (override) return override.endsWith('/') ? override : `${override}/`
  if (location && LANDING_HOSTS.has(location.hostname)) return '/models/'
  return REMOTE_MODELS_BASE
}

function isFile(value: unknown): value is PrerenderFile {
  return !!value && typeof value === 'object'
    && typeof (value as PrerenderFile).file === 'string'
    // A bare file name only: the manifest must not steer the loader elsewhere.
    && /^[A-Za-z0-9._-]+\.glb$/.test((value as PrerenderFile).file)
}

/** Parse a manifest body; null for anything that is not a v2 model list. */
export function parsePrerenderManifest(body: unknown): PrerenderManifest | null {
  if (!body || typeof body !== 'object') return null
  const raw = body as Partial<PrerenderManifest>
  if (!Array.isArray(raw.models)) return null
  // v1 manifests list uncompressed `<slug>.glb` files the Studio has no use for.
  if (typeof raw.version !== 'number' || raw.version < 2) return null
  return raw as PrerenderManifest
}

/** The preview for `slug`, or null when the manifest does not list a mesh for it. */
export function previewFromManifest(
  manifest: PrerenderManifest | null | undefined,
  slug: string | null | undefined,
  base: string,
): PrerenderedPreviewInfo | null {
  if (!manifest || !slug) return null
  const entry = manifest.models.find(m => m && m.slug === slug)
  if (!entry) return null
  const candidates: PrerenderCandidate[] = []
  if (isFile(entry.lod0)) candidates.push({ url: `${base}${entry.lod0.file}`, lod: 'lod0' })
  if (isFile(entry.lod1)) candidates.push({ url: `${base}${entry.lod1.file}`, lod: 'lod1' })
  if (candidates.length === 0) return null
  const pin = manifest.source?.commons_pin
  return {
    slug,
    candidates,
    commonsPin: typeof pin === 'string' && pin ? pin : null,
    generated: typeof manifest.generated === 'string' ? manifest.generated : null,
  }
}

interface CacheSlot {
  at: number
  ttl: number
  value: Promise<PrerenderManifest | null>
  settled: PrerenderManifest | null | undefined
}

const cache = new Map<string, CacheSlot>()

/**
 * The manifest at `base`, fetched at most once per TTL per base. Resolves to
 * null on any failure; never rejects and never logs.
 */
export function loadPrerenderManifest(
  base: string = resolveModelsBase(),
  now: number = Date.now(),
): Promise<PrerenderManifest | null> {
  const slot = cache.get(base)
  if (slot && now - slot.at <= slot.ttl) return slot.value
  const next: CacheSlot = { at: now, ttl: MANIFEST_TTL_MS, value: Promise.resolve(null), settled: undefined }
  next.value = (async () => {
    try {
      // Plain GET: no credentials, no auth header — the files are public and a
      // cross-origin request with either would need a preflight we do not serve.
      const response = await fetch(`${base}manifest.json`, { credentials: 'omit' })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const parsed = parsePrerenderManifest(await response.json())
      if (!parsed) throw new Error('not a v2 models manifest')
      next.settled = parsed
      return parsed
    } catch {
      next.ttl = MANIFEST_FAILURE_TTL_MS
      next.settled = null
      return null
    }
  })()
  cache.set(base, next)
  return next.value
}

/**
 * The preview for `slug` if the manifest is already in memory, without
 * fetching. `undefined` means "not known yet"; `null` means "no preview".
 */
export function peekPrerenderedPreview(
  slug: string | null | undefined,
  base: string = resolveModelsBase(),
): PrerenderedPreviewInfo | null | undefined {
  const slot = cache.get(base)
  if (!slot || slot.settled === undefined) return undefined
  return previewFromManifest(slot.settled, slug, base)
}

/** Test seam: forget every cached manifest. */
export function resetPrerenderManifestCache(): void {
  cache.clear()
}

/**
 * True when the current configuration is not the one the preview shows: a
 * different mode than the manifest's first, or any declared parameter moved
 * off its default. Parameters the manifest does not declare are ignored.
 */
export function differsFromPrerenderedDefault(
  mode: string | null | undefined,
  defaultMode: string | null | undefined,
  params: Record<string, unknown>,
  defaults: Record<string, unknown>,
): boolean {
  if (defaultMode && mode && mode !== defaultMode) return true
  for (const key of Object.keys(defaults)) {
    if (!(key in params)) continue
    if (JSON.stringify(params[key]) !== JSON.stringify(defaults[key])) return true
  }
  return false
}
