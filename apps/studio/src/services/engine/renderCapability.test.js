import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  staticCapabilityCeiling,
  classifyCapability,
  readCapabilitySignals,
  hasSimd,
  getDeviceCapability,
  probeDeviceCapability,
  resetDeviceCapability,
  getPlacementPreference,
  setPlacementPreference,
  subscribePlacementPreference,
  resetPlacementPreferenceCache,
  CAPABILITY_VERSION,
  CAPABILITY_TTL_MS,
  PROBE_FAILURE_TTL_MS,
  recordTtlMs,
  BENCHMARK_CAPABLE_MS,
  BENCHMARK_LIMITED_MS,
} from './renderCapability'

/** A machine with nothing wrong with it. */
const HEALTHY = {
  wasm: true,
  simd: true,
  cores: 8,
  memoryGb: 8,
  mobile: false,
  crossOriginIsolated: false,
  saveData: false,
  reducedData: false,
}

const signals = (overrides = {}) => ({ ...HEALTHY, ...overrides })

describe('staticCapabilityCeiling', () => {
  it('calls a healthy desktop capable', () => {
    expect(staticCapabilityCeiling(signals())).toBe('capable')
  })

  it('calls a browser with no WebAssembly incapable', () => {
    expect(staticCapabilityCeiling(signals({ wasm: false }))).toBe('incapable')
  })

  it('treats an unknown deviceMemory as unknown, NOT as 4 GB', () => {
    // The bug this replaces: `navigator.deviceMemory || 4` invented a value for
    // every Firefox and Safari visitor. An absent signal must not demote — and
    // must not promote either; the benchmark decides those machines.
    expect(staticCapabilityCeiling(signals({ memoryGb: null }))).toBe('capable')
  })

  it('treats an unknown hardwareConcurrency as unknown', () => {
    expect(staticCapabilityCeiling(signals({ cores: null }))).toBe('capable')
  })

  it('demotes a machine that reports few cores', () => {
    expect(staticCapabilityCeiling(signals({ cores: 3 }))).toBe('limited')
    expect(staticCapabilityCeiling(signals({ cores: 4 }))).toBe('capable')
  })

  it('demotes a machine that reports little memory, and rules out under 2 GB', () => {
    expect(staticCapabilityCeiling(signals({ memoryGb: 2 }))).toBe('limited')
    expect(staticCapabilityCeiling(signals({ memoryGb: 1 }))).toBe('incapable')
  })

  it('rules out a single core outright', () => {
    expect(staticCapabilityCeiling(signals({ cores: 1 }))).toBe('incapable')
  })

  it('demotes mobile even when the numbers look fine', () => {
    expect(staticCapabilityCeiling(signals({ mobile: true }))).toBe('limited')
  })

  it('leaves an unknown mobile signal alone', () => {
    expect(staticCapabilityCeiling(signals({ mobile: null }))).toBe('capable')
  })

  it('respects Save-Data and prefers-reduced-data — the bundle is a download', () => {
    expect(staticCapabilityCeiling(signals({ saveData: true }))).toBe('limited')
    expect(staticCapabilityCeiling(signals({ reducedData: true }))).toBe('limited')
  })

  it('demotes a machine without SIMD', () => {
    expect(staticCapabilityCeiling(signals({ simd: false }))).toBe('limited')
  })
})

describe('classifyCapability', () => {
  it('returns the static ceiling when nothing has been measured', () => {
    expect(classifyCapability(signals(), null)).toBe('capable')
    expect(classifyCapability(signals({ mobile: true }), null)).toBe('limited')
  })

  it('keeps a fast machine capable', () => {
    expect(classifyCapability(signals(), 45)).toBe('capable')
    expect(classifyCapability(signals(), BENCHMARK_CAPABLE_MS)).toBe('capable')
  })

  it('demotes a slow machine to limited', () => {
    expect(classifyCapability(signals(), BENCHMARK_CAPABLE_MS + 1)).toBe('limited')
    expect(classifyCapability(signals(), BENCHMARK_LIMITED_MS)).toBe('limited')
  })

  it('rules out a machine slower than the limited threshold', () => {
    expect(classifyCapability(signals(), BENCHMARK_LIMITED_MS + 1)).toBe('incapable')
  })

  it('never promotes past the static ceiling — a fast phone is still a phone', () => {
    expect(classifyCapability(signals({ mobile: true }), 10)).toBe('limited')
  })

  it('rescues a machine whose signals the browser withholds', () => {
    // Firefox/Safari report no deviceMemory. Under the old heuristic they were
    // judged on an invented 4 GB; here they are judged on what they measured.
    expect(classifyCapability(signals({ memoryGb: null, cores: null }), 80)).toBe('capable')
    expect(classifyCapability(signals({ memoryGb: null, cores: null }), 5000)).toBe('incapable')
  })

  it('ignores a nonsensical measurement rather than trusting it', () => {
    expect(classifyCapability(signals(), NaN)).toBe('capable')
    expect(classifyCapability(signals(), -1)).toBe('capable')
  })

  it('keeps a WebAssembly-less browser incapable however fast it measured', () => {
    expect(classifyCapability(signals({ wasm: false }), 1)).toBe('incapable')
  })
})

describe('hasSimd', () => {
  it('detects SIMD on an engine that supports it', () => {
    // Node 22 (and every browser the studio targets) validates the probe.
    // A mistyped module would validate nowhere, so this also guards the bytes.
    expect(hasSimd()).toBe(true)
  })

  it('reports false rather than throwing when validate is missing', () => {
    const original = WebAssembly.validate
    try {
      WebAssembly.validate = undefined
      expect(hasSimd()).toBe(false)
    } finally {
      WebAssembly.validate = original
    }
  })
})

describe('readCapabilitySignals', () => {
  afterEach(() => { vi.unstubAllGlobals() })

  it('reads a full navigator', () => {
    vi.stubGlobal('navigator', {
      hardwareConcurrency: 12,
      deviceMemory: 16,
      userAgentData: { mobile: false },
      connection: { saveData: false },
      userAgent: 'Mozilla/5.0',
    })
    const s = readCapabilitySignals()
    expect(s).toMatchObject({ cores: 12, memoryGb: 16, mobile: false, saveData: false })
  })

  it('reports null — not a guess — for signals the browser withholds', () => {
    vi.stubGlobal('navigator', { userAgent: '' })
    const s = readCapabilitySignals()
    expect(s.cores).toBeNull()
    expect(s.memoryGb).toBeNull()
    expect(s.mobile).toBeNull()
  })

  it('falls back to the UA string when userAgentData is absent', () => {
    vi.stubGlobal('navigator', { userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari' })
    expect(readCapabilitySignals().mobile).toBe(true)
  })

  it('honours Save-Data', () => {
    vi.stubGlobal('navigator', { userAgent: 'x', connection: { saveData: true } })
    expect(readCapabilitySignals().saveData).toBe(true)
  })
})

describe('getDeviceCapability / probeDeviceCapability', () => {
  beforeEach(() => {
    localStorage.clear()
    resetDeviceCapability()
    vi.stubGlobal('navigator', { hardwareConcurrency: 8, deviceMemory: 8, userAgent: 'desktop' })
  })
  afterEach(() => { vi.unstubAllGlobals() })

  it('answers synchronously from static signals before any probe', () => {
    const record = getDeviceCapability()
    expect(record.version).toBe(CAPABILITY_VERSION)
    expect(record.benchmarkMs).toBeNull()
    expect(record.tier).toBe('capable')
  })

  it('does NOT persist an unmeasured guess', () => {
    getDeviceCapability()
    expect(localStorage.getItem(`y4d.render_capability.v${CAPABILITY_VERSION}`)).toBeNull()
  })

  it('persists a measured record and reuses it', async () => {
    const run = vi.fn(async () => 120)
    const record = await probeDeviceCapability(run)
    expect(record.benchmarkMs).toBe(120)
    expect(record.tier).toBe('capable')
    expect(run).toHaveBeenCalledTimes(1)

    resetPreferenceOnly()
    await probeDeviceCapability(run)
    expect(run).toHaveBeenCalledTimes(1) // served from storage, not re-measured
  })

  it('shares one probe between concurrent callers', async () => {
    let resolveBench
    const run = vi.fn(() => new Promise(r => { resolveBench = r }))
    const a = probeDeviceCapability(run)
    const b = probeDeviceCapability(run)
    resolveBench(80)
    await Promise.all([a, b])
    expect(run).toHaveBeenCalledTimes(1)
  })

  it('classifies a device whose benchmark cannot even start as incapable', async () => {
    const record = await probeDeviceCapability(async () => { throw new Error('no wasm') })
    expect(record.tier).toBe('incapable')
    expect(record.benchmarkMs).toBeNull()
    expect(record.probeFailed).toBe(true)
  })

  it('trusts a failed-probe verdict for an hour, not a week', async () => {
    expect(PROBE_FAILURE_TTL_MS).toBe(60 * 60 * 1000)
    expect(recordTtlMs({ probeFailed: true })).toBe(PROBE_FAILURE_TTL_MS)
    expect(recordTtlMs({})).toBe(CAPABILITY_TTL_MS)

    await probeDeviceCapability(async () => { throw new Error('cdn down') })
    const key = `y4d.render_capability.v${CAPABILITY_VERSION}`
    const stored = JSON.parse(localStorage.getItem(key))
    expect(stored.tier).toBe('incapable')

    // Age it past the failure TTL but well inside the week: the stored verdict
    // must lapse, so the synchronous read falls back to the static signals
    // (a healthy machine reads capable) instead of a week of server renders.
    stored.at = Date.now() - PROBE_FAILURE_TTL_MS - 1
    localStorage.setItem(key, JSON.stringify(stored))
    resetPreferenceOnly()
    expect(getDeviceCapability().tier).not.toBe('incapable')
    expect(getDeviceCapability().benchmarkMs).toBeNull()
  })

  it('re-probes once the record is older than the TTL', async () => {
    const run = vi.fn(async () => 100)
    await probeDeviceCapability(run)

    const key = `y4d.render_capability.v${CAPABILITY_VERSION}`
    const stale = JSON.parse(localStorage.getItem(key))
    stale.at = Date.now() - CAPABILITY_TTL_MS - 1
    localStorage.setItem(key, JSON.stringify(stale))
    resetPreferenceOnly()

    await probeDeviceCapability(run)
    expect(run).toHaveBeenCalledTimes(2)
  })

  it('discards a record written by an older version', () => {
    localStorage.setItem(
      `y4d.render_capability.v${CAPABILITY_VERSION}`,
      JSON.stringify({ version: CAPABILITY_VERSION - 1, tier: 'incapable', signals: {}, at: Date.now() }),
    )
    resetPreferenceOnly()
    expect(getDeviceCapability().tier).toBe('capable')
  })

  it('survives corrupt storage', () => {
    localStorage.setItem(`y4d.render_capability.v${CAPABILITY_VERSION}`, 'not json{')
    resetPreferenceOnly()
    expect(() => getDeviceCapability()).not.toThrow()
    expect(getDeviceCapability().tier).toBe('capable')
  })

  it('survives localStorage throwing on every access', () => {
    const original = globalThis.localStorage
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      get() { throw new Error('storage disabled') },
    })
    try {
      resetPreferenceOnly()
      expect(() => getDeviceCapability()).not.toThrow()
    } finally {
      Object.defineProperty(globalThis, 'localStorage', { configurable: true, writable: true, value: original })
    }
  })

  /** Drop only the in-memory cache, leaving whatever storage holds. */
  function resetPreferenceOnly() {
    // resetDeviceCapability also clears storage, which several cases above need
    // to survive; this reaches the same memory cache via a fresh TTL miss.
    const key = `y4d.render_capability.v${CAPABILITY_VERSION}`
    const kept = (() => { try { return localStorage.getItem(key) } catch { return null } })()
    resetDeviceCapability()
    if (kept !== null) { try { localStorage.setItem(key, kept) } catch { /* ignore */ } }
  }
})

describe('render_placement_preference', () => {
  beforeEach(() => {
    localStorage.clear()
    resetPlacementPreferenceCache()
  })

  it('defaults to auto', () => {
    expect(getPlacementPreference()).toBe('auto')
  })

  it('round-trips browser and server', () => {
    setPlacementPreference('browser')
    resetPlacementPreferenceCache()
    expect(getPlacementPreference()).toBe('browser')

    setPlacementPreference('server')
    resetPlacementPreferenceCache()
    expect(getPlacementPreference()).toBe('server')
  })

  it('stores nothing for auto — the absence IS the default', () => {
    setPlacementPreference('server')
    setPlacementPreference('auto')
    expect(localStorage.getItem('y4d.render_placement_preference.v1')).toBeNull()
    expect(getPlacementPreference()).toBe('auto')
  })

  it('degrades an unrecognised stored value to auto instead of coercing it', () => {
    localStorage.setItem('y4d.render_placement_preference.v1', 'brwoser')
    resetPlacementPreferenceCache()
    expect(getPlacementPreference()).toBe('auto')
  })

  it('notifies subscribers on change', () => {
    const seen = []
    const unsubscribe = subscribePlacementPreference(p => seen.push(p))
    setPlacementPreference('server')
    setPlacementPreference('browser')
    unsubscribe()
    setPlacementPreference('auto')
    expect(seen).toEqual(['server', 'browser'])
  })

  it('keeps notifying the other subscribers when one throws', () => {
    const seen = []
    const a = subscribePlacementPreference(() => { throw new Error('bad subscriber') })
    const b = subscribePlacementPreference(p => seen.push(p))
    expect(() => setPlacementPreference('server')).not.toThrow()
    expect(seen).toEqual(['server'])
    a(); b()
  })
})
