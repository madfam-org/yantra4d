import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  REMOTE_MODELS_BASE,
  MANIFEST_TTL_MS,
  MANIFEST_FAILURE_TTL_MS,
  resolveModelsBase,
  parsePrerenderManifest,
  previewFromManifest,
  loadPrerenderManifest,
  peekPrerenderedPreview,
  resetPrerenderManifestCache,
  differsFromPrerenderedDefault,
} from './prerenderedPreview'

// The shape apps/landing/public/models/manifest.json has (v2, 2026-09-19).
const manifest = {
  version: 2,
  generated: '2026-09-19T18:46:49Z',
  source: { kind: 'render-api', commons_pin: 'f2c578f78037c37f0f29fe0571b946aeeb45bc0f' },
  models: [
    { slug: 'gridfinity', size: 10288, lod1: { file: 'gridfinity.lod1.glb', bytes: 10288 } },
    { slug: 'torus-knot', lod0: { file: 'torus-knot.lod0.glb', bytes: 50000 }, lod1: { file: 'torus-knot.lod1.glb', bytes: 9000 } },
    { slug: 'evil', lod1: { file: '../../api/secrets.glb' } },
  ],
}

function okResponse(body: unknown) {
  return { ok: true, status: 200, json: async () => body } as Response
}

beforeEach(() => { resetPrerenderManifestCache() })
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('resolveModelsBase', () => {
  it('reads the landing cross-origin from the Studio host and localhost', () => {
    expect(resolveModelsBase({}, { hostname: 'app.yantra4d.com' })).toBe(REMOTE_MODELS_BASE)
    expect(resolveModelsBase({}, { hostname: 'localhost' })).toBe('https://yantra4d.com/models/')
    expect(resolveModelsBase({}, null)).toBe(REMOTE_MODELS_BASE)
  })

  it('reads same-origin when served next to the landing files', () => {
    expect(resolveModelsBase({}, { hostname: 'yantra4d.com' })).toBe('/models/')
    expect(resolveModelsBase({}, { hostname: 'www.yantra4d.com' })).toBe('/models/')
  })

  it('honours VITE_PRERENDER_MODELS_BASE, adding the trailing slash', () => {
    expect(resolveModelsBase({ VITE_PRERENDER_MODELS_BASE: 'http://localhost:4321/models' }, { hostname: 'localhost' }))
      .toBe('http://localhost:4321/models/')
  })
})

describe('parsePrerenderManifest', () => {
  it('accepts a v2 model list and rejects everything else', () => {
    expect(parsePrerenderManifest(manifest)).toBe(manifest)
    expect(parsePrerenderManifest({ models: [] })).toBeNull() // v1: uncompressed, unbudgeted
    expect(parsePrerenderManifest({ version: 2 })).toBeNull()
    expect(parsePrerenderManifest('<!doctype html>')).toBeNull()
    expect(parsePrerenderManifest(null)).toBeNull()
  })
})

describe('previewFromManifest', () => {
  it('a hit lists lod0 before lod1 and carries the commons pin', () => {
    expect(previewFromManifest(manifest, 'torus-knot', '/models/')).toEqual({
      slug: 'torus-knot',
      candidates: [
        { url: '/models/torus-knot.lod0.glb', lod: 'lod0' },
        { url: '/models/torus-knot.lod1.glb', lod: 'lod1' },
      ],
      commonsPin: 'f2c578f78037c37f0f29fe0571b946aeeb45bc0f',
      generated: '2026-09-19T18:46:49Z',
    })
  })

  it('falls back to lod1 when the manifest has no lod0', () => {
    expect(previewFromManifest(manifest, 'gridfinity', REMOTE_MODELS_BASE)?.candidates)
      .toEqual([{ url: 'https://yantra4d.com/models/gridfinity.lod1.glb', lod: 'lod1' }])
  })

  it('a miss is null', () => {
    expect(previewFromManifest(manifest, 'ab-drive', '/models/')).toBeNull()
    expect(previewFromManifest(manifest, '', '/models/')).toBeNull()
    expect(previewFromManifest(null, 'gridfinity', '/models/')).toBeNull()
  })

  it('never builds a URL from a file name that is not a bare .glb', () => {
    expect(previewFromManifest(manifest, 'evil', '/models/')).toBeNull()
  })
})

describe('loadPrerenderManifest', () => {
  it('fetches once per base within the hour, without credentials', async () => {
    const fetchMock = vi.fn(async () => okResponse(manifest))
    vi.stubGlobal('fetch', fetchMock)
    const now = 1_000_000
    expect(await loadPrerenderManifest('/models/', now)).toBe(manifest)
    expect(await loadPrerenderManifest('/models/', now + MANIFEST_TTL_MS - 1)).toBe(manifest)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith('/models/manifest.json', { credentials: 'omit' })
    await loadPrerenderManifest('/models/', now + MANIFEST_TTL_MS + 1)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('fails silently: network error, non-200 and HTML all resolve to null without logging', async () => {
    const errors = vi.spyOn(console, 'error').mockImplementation(() => {})
    const warns = vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    expect(await loadPrerenderManifest('/a/')).toBeNull()
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 404, json: async () => ({}) }) as Response))
    expect(await loadPrerenderManifest('/b/')).toBeNull()
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError('html') } }) as unknown as Response))
    expect(await loadPrerenderManifest('/c/')).toBeNull()
    expect(errors).not.toHaveBeenCalled()
    expect(warns).not.toHaveBeenCalled()
  })

  it('retries a failure after the short failure TTL', async () => {
    const fetchMock = vi.fn(async () => { throw new TypeError('offline') })
    vi.stubGlobal('fetch', fetchMock)
    await loadPrerenderManifest('/models/', 0)
    await loadPrerenderManifest('/models/', MANIFEST_FAILURE_TTL_MS - 1)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    await loadPrerenderManifest('/models/', MANIFEST_FAILURE_TTL_MS + 1)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})

describe('peekPrerenderedPreview', () => {
  it('is undefined before the manifest settles, then the cached answer', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => okResponse(manifest)))
    expect(peekPrerenderedPreview('gridfinity', '/models/')).toBeUndefined()
    await loadPrerenderManifest('/models/')
    expect(peekPrerenderedPreview('gridfinity', '/models/')?.candidates[0].lod).toBe('lod1')
    expect(peekPrerenderedPreview('ab-drive', '/models/')).toBeNull()
  })
})

describe('differsFromPrerenderedDefault', () => {
  const defaults = { size: 42, label: 'A', on: true }
  it('is false at the defaults, in the first mode', () => {
    expect(differsFromPrerenderedDefault('bin', 'bin', { ...defaults }, defaults)).toBe(false)
  })
  it('is true when a declared parameter moves or the mode changes', () => {
    expect(differsFromPrerenderedDefault('bin', 'bin', { ...defaults, size: 43 }, defaults)).toBe(true)
    expect(differsFromPrerenderedDefault('grid', 'bin', { ...defaults }, defaults)).toBe(true)
  })
  it('ignores parameters the manifest does not declare', () => {
    expect(differsFromPrerenderedDefault('bin', 'bin', { ...defaults, target_material: 'pla' }, defaults)).toBe(false)
  })
})
