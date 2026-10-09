/**
 * The tier decision is a table, so it is tested as one. Two evaluations of the
 * same source must agree: the ES module (what islands import) and the inline
 * <head> bootstrap (what paints first) — the last block builds the inline text
 * exactly as BaseLayout does and runs it against fake globals.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  TIER_STORAGE_KEY,
  TIER_TTL_MS,
  TIER_VERSION,
  classifyTier,
  lowerTier,
  parseStoredTier,
  parseTierOverride,
  readCheapSignals,
  resolveTier,
} from './tier-core.js'
import { buildTierBootstrap } from './tier-bootstrap'
import { currentTier, probeWebgl, setUserTier, settleTier, userChoseTier } from './tier'

const base = {
  webgl2: null,
  softwareRenderer: null,
  reducedMotion: false,
  reducedData: false,
  bot: false,
  memoryGb: null,
  cores: null,
  mobile: null,
}

describe('classifyTier — the table', () => {
  const rows: Array<[string, Partial<typeof base>, 'still' | 'lite' | 'full']> = [
    ['everything unknown', {}, 'full'],
    ['desktop, 8 cores, 16 GB', { cores: 8, memoryGb: 16, mobile: false }, 'full'],
    ['no WebGL2', { webgl2: false, cores: 16 }, 'still'],
    ['software renderer', { softwareRenderer: true, cores: 16, memoryGb: 32 }, 'still'],
    ['prefers-reduced-motion', { reducedMotion: true }, 'still'],
    ['save-data / reduced-data', { reducedData: true, cores: 8 }, 'still'],
    ['crawler', { bot: true }, 'still'],
    ['memory known < 2 GB', { memoryGb: 1 }, 'still'],
    ['single core', { cores: 1 }, 'still'],
    ['mobile', { mobile: true, cores: 8, memoryGb: 8 }, 'lite'],
    ['cores known < 4', { cores: 2 }, 'lite'],
    ['memory known < 4 GB', { memoryGb: 2 }, 'lite'],
    ['Firefox/Safari: memory withheld, 4 cores', { memoryGb: null, cores: 4, mobile: false }, 'full'],
    ['WebGL2 probed fine on a desktop', { webgl2: true, softwareRenderer: false, cores: 8 }, 'full'],
  ]
  it.each(rows)('%s → %s', (_label, signals, expected) => {
    expect(classifyTier({ ...base, ...signals })).toBe(expected)
  })

  it('never lets an unknown signal demote', () => {
    expect(classifyTier({ ...base, memoryGb: null, cores: null, mobile: null, webgl2: null })).toBe('full')
  })

  it('tolerates a missing argument', () => {
    expect(classifyTier(undefined as any)).toBe('full')
  })
})

describe('lowerTier', () => {
  it('a probe can only demote', () => {
    expect(lowerTier('full', 'lite')).toBe('lite')
    expect(lowerTier('lite', 'full')).toBe('lite')
    expect(lowerTier('still', 'full')).toBe('still')
    expect(lowerTier('full', 'full')).toBe('full')
  })
})

describe('parseTierOverride', () => {
  it('accepts the three tiers, case-insensitively, anywhere in the query', () => {
    expect(parseTierOverride('?tier=still')).toBe('still')
    expect(parseTierOverride('?a=1&tier=Lite')).toBe('lite')
    expect(parseTierOverride('?tier=FULL&b=2')).toBe('full')
  })
  it('ignores anything else rather than coercing it', () => {
    expect(parseTierOverride('?tier=ultra')).toBeNull()
    expect(parseTierOverride('?tier=')).toBeNull()
    expect(parseTierOverride('?tiers=full')).toBeNull()
    expect(parseTierOverride('')).toBeNull()
    expect(parseTierOverride(undefined as any)).toBeNull()
  })
})

describe('parseStoredTier', () => {
  const now = 1_700_000_000_000
  const record = (extra: Record<string, unknown>) =>
    JSON.stringify({ version: TIER_VERSION, tier: 'lite', at: now - 1000, ...extra })

  it('returns a fresh measured record', () => {
    expect(parseStoredTier(record({ probed: true }), now)?.tier).toBe('lite')
  })
  it('expires a measured record after the TTL', () => {
    expect(parseStoredTier(record({ probed: true, at: now - TIER_TTL_MS - 1 }), now)).toBeNull()
  })
  it('never expires a visitor choice', () => {
    expect(parseStoredTier(record({ user: true, at: now - 10 * TIER_TTL_MS }), now)?.tier).toBe('lite')
  })
  it('rejects malformed, foreign-version and unknown-tier records', () => {
    expect(parseStoredTier('not json', now)).toBeNull()
    expect(parseStoredTier(record({ version: 99 }), now)).toBeNull()
    expect(parseStoredTier(record({ tier: 'ultra' }), now)).toBeNull()
    expect(parseStoredTier(record({ at: 'yesterday' }), now)).toBeNull()
    expect(parseStoredTier(null, now)).toBeNull()
  })
})

describe('readCheapSignals', () => {
  const win = (nav: Record<string, unknown>, media: Record<string, boolean> = {}) =>
    ({
      navigator: nav,
      matchMedia: (q: string) => ({ matches: media[q] === true }),
    }) as unknown as Window

  it('reads what the browser exposes and leaves the rest null', () => {
    const s = readCheapSignals(win({ userAgent: 'Mozilla/5.0 (X11; Linux) Firefox/130.0', hardwareConcurrency: 8 }))
    expect(s).toMatchObject({ webgl2: null, softwareRenderer: null, cores: 8, memoryGb: null, mobile: false, bot: false })
  })
  it('flags mobile from userAgentData first, UA second', () => {
    expect(readCheapSignals(win({ userAgentData: { mobile: true }, userAgent: 'Desktop' })).mobile).toBe(true)
    expect(readCheapSignals(win({ userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)' })).mobile).toBe(true)
  })
  it('flags crawlers and headless agents', () => {
    expect(readCheapSignals(win({ userAgent: 'Mozilla/5.0 (compatible; Googlebot/2.1)' })).bot).toBe(true)
    expect(readCheapSignals(win({ userAgent: 'Mozilla/5.0 HeadlessChrome/128.0' })).bot).toBe(true)
    expect(readCheapSignals(win({ userAgent: 'Mozilla/5.0 Chrome/128.0 Safari/537.36' })).bot).toBe(false)
  })
  it('reads reduced motion, reduced data and Save-Data', () => {
    expect(readCheapSignals(win({}, { '(prefers-reduced-motion: reduce)': true })).reducedMotion).toBe(true)
    expect(readCheapSignals(win({}, { '(prefers-reduced-data: reduce)': true })).reducedData).toBe(true)
    expect(readCheapSignals(win({ connection: { saveData: true } })).reducedData).toBe(true)
  })
  it('survives a window with no matchMedia and a navigator that throws nothing', () => {
    expect(readCheapSignals({ navigator: {} } as unknown as Window).mobile).toBeNull()
    expect(readCheapSignals(undefined as unknown as Window).cores).toBeNull()
  })
})

describe('resolveTier precedence', () => {
  const now = 1_700_000_000_000
  const stored = JSON.stringify({ version: TIER_VERSION, tier: 'lite', at: now - 5, probed: true })
  it('override beats stored beats signals', () => {
    expect(resolveTier({ search: '?tier=still', storedRaw: stored, now, signals: base })).toEqual({ tier: 'still', source: 'override' })
    expect(resolveTier({ search: '', storedRaw: stored, now, signals: base })).toEqual({ tier: 'lite', source: 'stored' })
    expect(resolveTier({ search: '', storedRaw: null, now, signals: base })).toEqual({ tier: 'full', source: 'signals' })
  })
  it('names a visitor choice as such', () => {
    const user = JSON.stringify({ version: TIER_VERSION, tier: 'still', at: 1, user: true })
    expect(resolveTier({ search: '', storedRaw: user, now, signals: base })).toEqual({ tier: 'still', source: 'user' })
  })
})

// ─── The inline bootstrap, evaluated the way BaseLayout ships it ───────────

type FakeDom = {
  html: Map<string, string>
  search: string
  storage: Record<string, string>
  nav: Record<string, unknown>
  media?: Record<string, boolean>
  throwOnStorage?: boolean
}

function runBootstrap(dom: FakeDom) {
  const src = buildTierBootstrap()
  const root = {
    setAttribute: (k: string, v: string) => dom.html.set(k, v),
    getAttribute: (k: string) => dom.html.get(k) ?? null,
  }
  const fakeDocument = { documentElement: root }
  const storage = {
    getItem: (k: string) => {
      if (dom.throwOnStorage) throw new Error('SecurityError')
      return dom.storage[k] ?? null
    },
  }
  const fakeWindow = {
    location: { search: dom.search },
    localStorage: storage,
    navigator: dom.nav,
    matchMedia: (q: string) => ({ matches: dom.media?.[q] === true }),
  }
  // Classic-script semantics: the stripped core declares globals the bootstrap reads.
  const fn = new Function('window', 'document', 'navigator', 'Date', src)
  fn(fakeWindow, fakeDocument, dom.nav, Date)
  return { tier: dom.html.get('data-tier'), source: dom.html.get('data-tier-source') }
}

describe('inline bootstrap parity', () => {
  it('ships no ESM syntax and sets the tier from cheap signals', () => {
    const src = buildTierBootstrap()
    expect(src).not.toMatch(/^\s*export\s/m)
    expect(src).not.toMatch(/^\s*import\s/m)
    const dom: FakeDom = { html: new Map(), search: '', storage: {}, nav: { userAgent: 'Mozilla/5.0 Chrome/128', hardwareConcurrency: 8, deviceMemory: 8 } }
    expect(runBootstrap(dom)).toEqual({ tier: 'full', source: 'signals' })
  })

  it('agrees with the module on a table of devices', () => {
    const devices: Array<[Record<string, unknown>, Record<string, boolean> | undefined]> = [
      [{ userAgent: 'Mozilla/5.0 (iPhone)', hardwareConcurrency: 6 }, undefined],
      [{ userAgent: 'Mozilla/5.0 Chrome/128', hardwareConcurrency: 2 }, undefined],
      [{ userAgent: 'Mozilla/5.0 Chrome/128', deviceMemory: 1 }, undefined],
      [{ userAgent: 'Googlebot/2.1' }, undefined],
      [{ userAgent: 'Mozilla/5.0 Firefox/130' }, { '(prefers-reduced-motion: reduce)': true }],
      [{ userAgent: 'Mozilla/5.0 Firefox/130' }, undefined],
    ]
    for (const [nav, media] of devices) {
      const expected = classifyTier(readCheapSignals({ navigator: nav, matchMedia: (q: string) => ({ matches: media?.[q] === true }) } as unknown as Window))
      expect(runBootstrap({ html: new Map(), search: '', storage: {}, nav, media }).tier).toBe(expected)
    }
  })

  it('honours ?tier= over a stored record over signals', () => {
    const stored = { [TIER_STORAGE_KEY]: JSON.stringify({ version: TIER_VERSION, tier: 'lite', at: Date.now(), probed: true }) }
    const nav = { userAgent: 'Mozilla/5.0 Chrome/128', hardwareConcurrency: 8 }
    expect(runBootstrap({ html: new Map(), search: '?tier=still', storage: stored, nav })).toEqual({ tier: 'still', source: 'override' })
    expect(runBootstrap({ html: new Map(), search: '', storage: stored, nav })).toEqual({ tier: 'lite', source: 'stored' })
    const user = { [TIER_STORAGE_KEY]: JSON.stringify({ version: TIER_VERSION, tier: 'still', at: 1, user: true }) }
    expect(runBootstrap({ html: new Map(), search: '', storage: user, nav })).toEqual({ tier: 'still', source: 'user' })
  })

  it('decides from signals when storage throws, and fails closed to still on any other error', () => {
    const nav = { userAgent: 'Mozilla/5.0 Chrome/128', hardwareConcurrency: 8 }
    expect(runBootstrap({ html: new Map(), search: '', storage: {}, nav, throwOnStorage: true })).toEqual({ tier: 'full', source: 'signals' })
    const broken: FakeDom = { html: new Map(), search: '', storage: {}, nav: null as unknown as Record<string, unknown> }
    // A navigator of null makes readCheapSignals fall back to defaults rather than throw…
    expect(['full', 'still']).toContain(runBootstrap(broken).tier)
    // …so force a real exception: location missing entirely.
    const src = buildTierBootstrap()
    const html = new Map<string, string>()
    const fn = new Function('window', 'document', 'navigator', 'Date', src)
    fn({}, { documentElement: { setAttribute: (k: string, v: string) => html.set(k, v) } }, {}, Date)
    expect(html.get('data-tier')).toBe('still')
    expect(html.get('data-tier-source')).toBe('error')
  })
})

// ─── tier.ts against jsdom ─────────────────────────────────────────────────

describe('tier.ts', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-tier')
    document.documentElement.removeAttribute('data-tier-source')
    // jsdom has no WebGL and logs a "not implemented" error for every
    // getContext call; answer null quietly, which is also what a browser with
    // no WebGL2 does.
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('reads the markup default as still when the bootstrap did not run', () => {
    expect(currentTier()).toEqual({ tier: 'still', source: 'markup' })
  })

  it('probeWebgl reports no WebGL2 in jsdom without throwing', () => {
    expect(probeWebgl()).toEqual({ webgl2: false, softwareRenderer: false, renderer: null })
  })

  it('settleTier demotes a signals-decided full to still when the probe finds no WebGL2, and persists it', () => {
    document.documentElement.setAttribute('data-tier', 'full')
    document.documentElement.setAttribute('data-tier-source', 'signals')
    const state = settleTier(1_700_000_000_000)
    expect(state).toEqual({ tier: 'still', source: 'probe' })
    expect(document.documentElement.getAttribute('data-tier')).toBe('still')
    const stored = JSON.parse(localStorage.getItem(TIER_STORAGE_KEY)!)
    expect(stored).toMatchObject({ version: TIER_VERSION, tier: 'still', probed: true })
  })

  it('settleTier leaves an override and a visitor choice untouched', () => {
    document.documentElement.setAttribute('data-tier', 'full')
    document.documentElement.setAttribute('data-tier-source', 'override')
    expect(settleTier()).toEqual({ tier: 'full', source: 'override' })
    expect(localStorage.getItem(TIER_STORAGE_KEY)).toBeNull()

    document.documentElement.setAttribute('data-tier-source', 'user')
    expect(settleTier()).toEqual({ tier: 'full', source: 'user' })
  })

  it('setUserTier stores a non-expiring choice and null clears it', () => {
    setUserTier('still', 1)
    expect(userChoseTier(Number.MAX_SAFE_INTEGER)).toBe('still')
    setUserTier(null)
    expect(userChoseTier()).toBeNull()
  })
})
