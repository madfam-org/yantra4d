/**
 * Device capability probe for browser (WASM) rendering, plus the user's
 * render-placement preference.
 *
 * WHY THIS EXISTS
 * ---------------
 * Rendering in the visitor's browser is free — no server CPU, no queue, no rate
 * limit. Rendering on our server costs us money and costs the visitor a quota.
 * So the browser is the default, and this module answers the only question that
 * can justify overriding that default: *can this machine actually do it?*
 *
 * The old answer was one line — `hardwareConcurrency >= 4 && deviceMemory >= 4`
 * — and it was wrong in both directions. `deviceMemory` does not exist on
 * Firefox or Safari, so `|| 4` silently invented a value for roughly a third of
 * the web; and neither number says anything about how fast the machine actually
 * compiles WebAssembly. This module keeps the static signals as a *ceiling* and
 * settles the question with a measurement.
 *
 * UNKNOWN IS UNKNOWN. A signal the browser does not expose never demotes a
 * device and never promotes it. That is the whole fix for the Firefox/Safari
 * case: an absent `deviceMemory` means "we do not know", not "4 GB".
 */

export type CapabilityTier = 'capable' | 'limited' | 'incapable'
export type PlacementPreference = 'auto' | 'browser' | 'server'

export interface CapabilitySignals {
  /** WebAssembly exists at all. Without it the browser path is impossible. */
  wasm: boolean
  /** WebAssembly SIMD — a large constant factor for the OpenSCAD kernel. */
  simd: boolean
  /** `navigator.hardwareConcurrency`, or null when the browser withholds it. */
  cores: number | null
  /** `navigator.deviceMemory` in GB, or null on Firefox/Safari (NOT 4). */
  memoryGb: number | null
  /** True/false from `userAgentData.mobile` or a UA-string fallback; null if neither is readable. */
  mobile: boolean | null
  /** `crossOriginIsolated` — threaded WASM builds need it; recorded for diagnosis. */
  crossOriginIsolated: boolean
  /** `connection.saveData` — the visitor asked us not to spend their bytes. */
  saveData: boolean
  /** `prefers-reduced-data` media query — the same request, expressed in CSS. */
  reducedData: boolean
}

export interface CapabilityRecord {
  version: number
  tier: CapabilityTier
  signals: CapabilitySignals
  /** Wall ms for "instantiate + tiny reference render"; null when never benchmarked. */
  benchmarkMs: number | null
  /** Epoch ms the record was written. */
  at: number
  /**
   * True when the benchmark could not run at all (module failed to instantiate,
   * worker crashed, timed out). Such a record expires after
   * `PROBE_FAILURE_TTL_MS`, not `CAPABILITY_TTL_MS`: a CDN hiccup must not cost
   * a device a week of free browser rendering.
   */
  probeFailed?: boolean
}

/**
 * Bump to invalidate every stored record — e.g. after changing the reference
 * render, the thresholds, or the signal set. A stale record classified under
 * old rules is worse than no record.
 */
export const CAPABILITY_VERSION = 1

/** Re-probe after a week: hardware does not change, but browsers and builds do. */
export const CAPABILITY_TTL_MS = 7 * 24 * 60 * 60 * 1000
/** How long a "the benchmark could not run" verdict is trusted before re-probing. */
export const PROBE_FAILURE_TTL_MS = 60 * 60 * 1000

/** A record's lifetime: short for a failed probe, a week for a measurement. */
export function recordTtlMs(record: Pick<CapabilityRecord, 'probeFailed'>): number {
  return record.probeFailed ? PROBE_FAILURE_TTL_MS : CAPABILITY_TTL_MS
}

const CAPABILITY_KEY = `y4d.render_capability.v${CAPABILITY_VERSION}`
const PREFERENCE_KEY = 'y4d.render_placement_preference.v1'

/**
 * Benchmark thresholds, in wall milliseconds for "instantiate a fresh OpenSCAD
 * WASM module + render `$fn=64; cube(10);` to STL".
 *
 * Calibrated against the real `openscad-wasm@0.0.4` build measured on a
 * server-class x86 host under Node 22 (2026-09-01, 5 runs):
 *
 *     instantiate  median  42 ms  (119 ms on the very first, cold run)
 *     tiny render  median   3 ms
 *     combined     median  45 ms  (151 ms cold)
 *
 * That is the floor — a warm JIT with no other tab competing. Browser engines
 * on the same class of machine land within roughly 2-5x of it, and phones 5-15x.
 * The two thresholds below are therefore set at ~13x and ~55x the measured
 * floor: comfortably above any healthy desktop, and low enough that a device
 * which needs half a second just to compile a cube will never be handed a
 * cartridge that pulls in 56 BOSL2 files.
 *
 * The same lab measured what those cartridges actually cost in this build:
 * `gridfinity/cup.scad` (BOSL2, fn=32) 5.2 s, `relief/plaque.scad` with fonts
 * 5.5 s, `torus-knot` 1.0 s. A machine 55x slower than the reference turns the
 * 5 s cartridge into four minutes — which is a server render, not a browser one.
 */
export const BENCHMARK_CAPABLE_MS = 600
export const BENCHMARK_LIMITED_MS = 2500

/**
 * A 29-byte WebAssembly module containing `i32.const 0; i8x16.splat; drop`.
 * `i8x16.splat` (opcode 0xfd 0x0f) exists only under the fixed-width SIMD
 * proposal, so the module validates on a SIMD engine and fails to validate
 * everywhere else. Byte-for-byte the probe used by `wasm-feature-detect`;
 * verified against Node 22 (validates: true) rather than trusted from memory,
 * because a mistyped module validates as `false` on every engine and would
 * quietly classify the entire web as SIMD-less.
 */
const SIMD_PROBE = new Uint8Array([
  0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
  0x01, 0x04, 0x01, 0x60, 0x00, 0x00,
  0x03, 0x02, 0x01, 0x00,
  0x0a, 0x09, 0x01, 0x07, 0x00, 0x41, 0x00, 0xfd, 0x0f, 0x1a, 0x0b,
])

function safeGet(key: string): string | null {
  try {
    return globalThis.localStorage?.getItem(key) ?? null
  } catch {
    return null
  }
}

function safeSet(key: string, value: string): void {
  try {
    globalThis.localStorage?.setItem(key, value)
  } catch {
    /* private mode, quota, disabled storage — the probe still works, it just
       gets re-run next page load. Never let storage break rendering. */
  }
}

function safeRemove(key: string): void {
  try {
    globalThis.localStorage?.removeItem(key)
  } catch { /* see safeSet */ }
}

/** Detect WebAssembly SIMD without throwing on engines that lack `validate`. */
export function hasSimd(): boolean {
  try {
    return typeof WebAssembly?.validate === 'function' && WebAssembly.validate(SIMD_PROBE)
  } catch {
    return false
  }
}

interface NavigatorLike {
  hardwareConcurrency?: number
  deviceMemory?: number
  userAgent?: string
  userAgentData?: { mobile?: boolean }
  connection?: { saveData?: boolean }
}

/**
 * Read every static signal. Anything the browser does not expose comes back
 * null/false rather than a guess.
 */
export function readCapabilitySignals(): CapabilitySignals {
  const nav: NavigatorLike = (typeof navigator !== 'undefined' ? navigator : {}) as NavigatorLike

  const rawCores = nav.hardwareConcurrency
  const cores = typeof rawCores === 'number' && Number.isFinite(rawCores) && rawCores > 0
    ? rawCores
    : null

  const rawMem = nav.deviceMemory
  const memoryGb = typeof rawMem === 'number' && Number.isFinite(rawMem) && rawMem > 0
    ? rawMem
    : null

  let mobile: boolean | null = null
  if (typeof nav.userAgentData?.mobile === 'boolean') {
    mobile = nav.userAgentData.mobile
  } else if (typeof nav.userAgent === 'string' && nav.userAgent) {
    mobile = /Android|iPhone|iPad|iPod|Mobile|Silk|Kindle|Opera Mini/i.test(nav.userAgent)
  }

  let reducedData = false
  try {
    reducedData = typeof globalThis.matchMedia === 'function'
      && globalThis.matchMedia('(prefers-reduced-data: reduce)').matches === true
  } catch { /* jsdom and old engines throw on unknown features */ }

  return {
    wasm: typeof WebAssembly === 'object' && typeof WebAssembly?.instantiate === 'function',
    simd: hasSimd(),
    cores,
    memoryGb,
    mobile,
    crossOriginIsolated: globalThis.crossOriginIsolated === true,
    saveData: nav.connection?.saveData === true,
    reducedData,
  }
}

const TIER_ORDER: Record<CapabilityTier, number> = { incapable: 0, limited: 1, capable: 2 }

function worstOf(a: CapabilityTier, b: CapabilityTier): CapabilityTier {
  return TIER_ORDER[a] <= TIER_ORDER[b] ? a : b
}

/**
 * The static ceiling: the best tier the signals alone permit, before any
 * measurement. PURE — this is the half of the classifier that unit tests pin.
 *
 * Documented rules, in order:
 *   - no WebAssembly                    -> incapable   (nothing else can rescue it)
 *   - deviceMemory known and < 2 GB     -> incapable   (a 512 MB heap will not fit)
 *   - hardwareConcurrency known and 1   -> incapable   (a blocking render with no spare core)
 *   - Save-Data / prefers-reduced-data  -> limited     (the bundle is a download the user declined)
 *   - mobile                            -> limited     (battery and thermal budget, not just speed)
 *   - cores known and < 4               -> limited
 *   - deviceMemory known and < 4 GB     -> limited
 *   - no SIMD                           -> limited     (large constant factor in this kernel)
 *   - everything else / unknown         -> capable
 */
export function staticCapabilityCeiling(signals: CapabilitySignals): CapabilityTier {
  if (!signals.wasm) return 'incapable'
  if (signals.memoryGb !== null && signals.memoryGb < 2) return 'incapable'
  if (signals.cores !== null && signals.cores < 2) return 'incapable'

  let tier: CapabilityTier = 'capable'
  if (signals.saveData || signals.reducedData) tier = worstOf(tier, 'limited')
  if (signals.mobile === true) tier = worstOf(tier, 'limited')
  if (signals.cores !== null && signals.cores < 4) tier = worstOf(tier, 'limited')
  if (signals.memoryGb !== null && signals.memoryGb < 4) tier = worstOf(tier, 'limited')
  if (!signals.simd) tier = worstOf(tier, 'limited')
  return tier
}

/**
 * Final classification. PURE.
 *
 * The benchmark can only ever *lower* the static ceiling, never raise it: a
 * phone that compiles a cube quickly is still a phone, and a machine whose
 * signals we cannot read is judged entirely on what it measured.
 */
export function classifyCapability(
  signals: CapabilitySignals,
  benchmarkMs: number | null,
): CapabilityTier {
  const ceiling = staticCapabilityCeiling(signals)
  if (ceiling === 'incapable') return 'incapable'
  if (benchmarkMs === null || !Number.isFinite(benchmarkMs) || benchmarkMs < 0) return ceiling
  if (benchmarkMs > BENCHMARK_LIMITED_MS) return 'incapable'
  if (benchmarkMs > BENCHMARK_CAPABLE_MS) return worstOf(ceiling, 'limited')
  return ceiling
}

function isRecord(value: unknown): value is CapabilityRecord {
  if (!value || typeof value !== 'object') return false
  const r = value as Partial<CapabilityRecord>
  return r.version === CAPABILITY_VERSION
    && typeof r.at === 'number'
    && (r.tier === 'capable' || r.tier === 'limited' || r.tier === 'incapable')
    && typeof r.signals === 'object' && r.signals !== null
}

function readStoredRecord(now: number): CapabilityRecord | null {
  const raw = safeGet(CAPABILITY_KEY)
  if (!raw) return null
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    safeRemove(CAPABILITY_KEY)
    return null
  }
  if (!isRecord(parsed)) {
    safeRemove(CAPABILITY_KEY)
    return null
  }
  if (now - parsed.at > recordTtlMs(parsed)) return null
  return parsed
}

let _cached: CapabilityRecord | null = null

/**
 * The current capability record, synchronously.
 *
 * Returns the persisted record when one is fresh and version-matched. Otherwise
 * it classifies from static signals alone and returns that WITHOUT persisting —
 * an unmeasured guess must not masquerade as a probe result on the next load.
 */
export function getDeviceCapability(): CapabilityRecord {
  const now = Date.now()
  if (_cached && now - _cached.at <= recordTtlMs(_cached)) return _cached

  const stored = readStoredRecord(now)
  if (stored) {
    _cached = stored
    return stored
  }

  const signals = readCapabilitySignals()
  return {
    version: CAPABILITY_VERSION,
    tier: classifyCapability(signals, null),
    signals,
    benchmarkMs: null,
    at: now,
  }
}

/** The tier alone — the shape `decideRenderPlacement` actually consumes. */
export function getCapabilityTier(): CapabilityTier {
  return getDeviceCapability().tier
}

/** How the async probe obtains its measurement. Injected so tests stay pure. */
export type BenchmarkRunner = () => Promise<number>

let _probeInFlight: Promise<CapabilityRecord> | null = null

/**
 * Run the one-shot micro-benchmark (unless a fresh record already exists),
 * classify, persist, and return the record.
 *
 * Concurrent callers share one in-flight probe: the benchmark spins up a real
 * WASM module, and doing that three times because three components asked at
 * once would be exactly the waste this whole feature is trying to avoid.
 */
export async function probeDeviceCapability(
  runBenchmark: BenchmarkRunner,
  { force = false }: { force?: boolean } = {},
): Promise<CapabilityRecord> {
  const now = Date.now()
  if (!force) {
    const stored = readStoredRecord(now)
    if (stored && stored.benchmarkMs !== null) {
      _cached = stored
      return stored
    }
  }
  if (_probeInFlight) return _probeInFlight

  _probeInFlight = (async () => {
    const signals = readCapabilitySignals()

    // No WebAssembly at all: there is nothing to time, and trying would throw.
    if (!signals.wasm) {
      const record: CapabilityRecord = {
        version: CAPABILITY_VERSION,
        tier: 'incapable',
        signals,
        benchmarkMs: null,
        at: Date.now(),
      }
      _cached = record
      safeSet(CAPABILITY_KEY, JSON.stringify(record))
      return record
    }

    let benchmarkMs: number | null = null
    try {
      const ms = await runBenchmark()
      benchmarkMs = Number.isFinite(ms) && ms >= 0 ? ms : null
    } catch {
      // A benchmark that cannot even start is itself the answer: the browser
      // could not instantiate the module, so it cannot render with it either.
      // But it is a short-lived answer (`probeFailed`): the next page load
      // re-probes, and the stored verdict lapses after PROBE_FAILURE_TTL_MS.
      benchmarkMs = null
      const record: CapabilityRecord = {
        version: CAPABILITY_VERSION,
        tier: 'incapable',
        signals,
        benchmarkMs: null,
        at: Date.now(),
        probeFailed: true,
      }
      _cached = record
      safeSet(CAPABILITY_KEY, JSON.stringify(record))
      return record
    }

    const record: CapabilityRecord = {
      version: CAPABILITY_VERSION,
      tier: classifyCapability(signals, benchmarkMs),
      signals,
      benchmarkMs,
      at: Date.now(),
    }
    _cached = record
    safeSet(CAPABILITY_KEY, JSON.stringify(record))
    return record
  })().finally(() => { _probeInFlight = null })

  return _probeInFlight
}

/** Drop the cached record (memory + storage). Used by tests and the probe UI. */
export function resetDeviceCapability(): void {
  _cached = null
  _probeInFlight = null
  safeRemove(CAPABILITY_KEY)
}

// ── User preference ─────────────────────────────────────────────────────────

const PREFERENCES: readonly PlacementPreference[] = ['auto', 'browser', 'server']

function parsePreference(value: string | null): PlacementPreference | null {
  return (PREFERENCES as readonly string[]).includes(value ?? '')
    ? (value as PlacementPreference)
    : null
}

type PreferenceListener = (preference: PlacementPreference) => void
const _preferenceListeners = new Set<PreferenceListener>()
let _preferenceCache: PlacementPreference | null = null

/**
 * The visitor's explicit choice: `auto` (let the capability probe decide),
 * `browser` (never spend my server quota), `server` (my machine is busy).
 *
 * Defaults to `auto`. An unrecognised stored value degrades to `auto` rather
 * than being coerced — the same discipline `?render=` uses.
 */
export function getPlacementPreference(): PlacementPreference {
  if (_preferenceCache) return _preferenceCache
  _preferenceCache = parsePreference(safeGet(PREFERENCE_KEY)) ?? 'auto'
  return _preferenceCache
}

export function setPlacementPreference(preference: PlacementPreference): void {
  const next = parsePreference(preference) ?? 'auto'
  _preferenceCache = next
  if (next === 'auto') safeRemove(PREFERENCE_KEY)
  else safeSet(PREFERENCE_KEY, next)
  for (const listener of [..._preferenceListeners]) {
    try {
      listener(next)
    } catch { /* one bad subscriber must not stop the others */ }
  }
}

/** Subscribe to preference changes. Returns an unsubscribe function. */
export function subscribePlacementPreference(listener: PreferenceListener): () => void {
  _preferenceListeners.add(listener)
  return () => { _preferenceListeners.delete(listener) }
}

/** Test seam: forget the in-memory preference so storage is re-read. */
export function resetPlacementPreferenceCache(): void {
  _preferenceCache = null
}

// Another tab changing the preference should move this one too — the choice is
// about the machine, not about the tab.
if (typeof globalThis.addEventListener === 'function') {
  globalThis.addEventListener('storage', (event: Event) => {
    const e = event as StorageEvent
    if (e.key !== PREFERENCE_KEY) return
    const next = parsePreference(e.newValue) ?? 'auto'
    _preferenceCache = next
    for (const listener of [..._preferenceListeners]) {
      try {
        listener(next)
      } catch { /* see setPlacementPreference */ }
    }
  })
}
