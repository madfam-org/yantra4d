/**
 * Where a render runs: the visitor's browser, or our server.
 *
 * This module is deliberately PURE. Every input the decision depends on is
 * passed in; nothing here reads `window`, `localStorage`, the network, or
 * module-global state. That is what makes the precedence table below testable
 * as a table instead of as an integration test with six mocks — and it is the
 * reason the old `detectMode()` was impossible to reason about: it interleaved
 * an await, a module-global cache, and an env var with the actual policy.
 *
 * PRODUCT DIRECTIVE. The browser is the default. Rendering there is free for us
 * and unmetered for the visitor; rendering on the server costs money and burns
 * their hourly quota. A render only goes to the server when something concrete
 * says the browser cannot do it, or when the visitor asks for it.
 */

import type { CapabilityTier, PlacementPreference } from './renderCapability'

export type Placement = 'browser' | 'server'

/** Engines with no browser kernel. CadQuery and graph run OCCT/Python
 *  server-side; implicit evaluates SDFs in a server mesher. */
export const BROWSER_INCAPABLE_ENGINES: ReadonlySet<string> = new Set([
  'cadquery',
  'graph',
  'implicit',
])

/** Engines the platform recognises. Anything else is treated as openscad. */
export const KNOWN_ENGINES: ReadonlySet<string> = new Set([
  'openscad',
  'cadquery',
  'implicit',
  'graph',
])

/**
 * The narrowest manifest shape `effectiveModeEngine` needs.
 *
 * Deliberately free of an index signature on the mode objects: a structural
 * `[key: string]: unknown` there would refuse every stricter mode interface in
 * the codebase (an interface has no implicit index signature), which is exactly
 * the manifests that have to be passed in.
 */
export interface ModeEngineManifest {
  /** The project-level engine, already resolved by the API's `manifest.engine`. */
  engine?: string | null
  modes?: ReadonlyArray<{ id?: string; engine?: string; scad_file?: string }>
}

/**
 * The engine ONE MODE renders with. PURE.
 *
 * Engine is a per-mode property, not a per-project one. 8 of the 31
 * OpenSCAD-capable cartridges are dual-engine: `gridfinity` declares
 * `project.engine: "cadquery"` and then three modes with an explicit
 * `engine: "openscad"`. Reading the project engine alone would send those three
 * to the server forever, which is exactly the money this feature is trying to
 * stop spending.
 *
 * Mirrors `ProjectManifest.mode_engine()` in `apps/api/manifest.py`, highest
 * priority first:
 *
 *   1. An explicit, known `engine` on the mode.
 *   2. Inference from the mode's `scad_file`: `.graph.json` -> graph,
 *      `.py` / `.cq` -> cadquery.
 *   3. The project engine (default `openscad`).
 *
 * An `implicit` project is the exception: implicit fields are a whole-project
 * concern, so every mode is implicit and nothing overrides it.
 */
export function effectiveModeEngine(
  manifest: ModeEngineManifest | null | undefined,
  modeId?: string | null,
): string {
  const declared = manifest?.engine ?? 'openscad'
  const projectEngine = KNOWN_ENGINES.has(declared) ? declared : 'openscad'
  if (projectEngine === 'implicit') return 'implicit'

  if (modeId) {
    const mode = manifest?.modes?.find(m => m?.id === modeId)
    if (mode) {
      if (mode.engine && KNOWN_ENGINES.has(mode.engine)) return mode.engine
      const primary = String(mode.scad_file ?? '')
      if (primary.endsWith('.graph.json')) return 'graph'
      if (primary.endsWith('.py') || primary.endsWith('.cq')) return 'cadquery'
    }
  }

  return projectEngine
}

/**
 * Whether ANY mode of this cartridge could render in a browser.
 *
 * The answer surfaces where no single mode is in scope — the rate-limit banner
 * offering "browser rendering is still available", for instance. For a
 * dual-engine cartridge that is true even though the project engine is not
 * browser-capable.
 */
export function canRenderAnyModeInBrowser(manifest: ModeEngineManifest | null | undefined): boolean {
  const modes = manifest?.modes
  if (!modes?.length) return canRenderInBrowser(effectiveModeEngine(manifest, null))
  return modes.some(m => canRenderInBrowser(effectiveModeEngine(manifest, m?.id ?? null)))
}

export interface BundleInfo {
  /**
   * Whether the WASM bundle for this cartridge could be obtained.
   * `null` = not looked up yet (do not hold it against the browser).
   */
  available: boolean | null
  /**
   * Features the server determined the WASM build cannot execute for this
   * cartridge (e.g. `import()` of an external mesh). Empty/absent = none known.
   */
  unsupported?: string[] | null
  /**
   * `include`/`use` targets the server could not confine to the cartridge
   * directory or `libs/`, as `"<including path>: <target>"`.
   *
   * A browser render of a cartridge with a missing include does not merely look
   * different — it fails outright, or silently renders a different model. Same
   * consequence as `unsupported`, so it gets the same rule.
   */
  unresolved?: string[] | null
}

export interface PlacementInput {
  /** `manifest.engine`; absent/unknown is treated as openscad (see manifest.py). */
  engine?: string | null
  /** `?render=` / `VITE_RENDER_MODE`, already parsed. */
  override?: 'backend' | 'wasm' | null
  /** The visitor's stored `render_placement_preference`. */
  userPreference?: PlacementPreference
  /** Result of the capability probe. */
  capabilityTier?: CapabilityTier
  /** What we know about this cartridge's WASM bundle. */
  bundle?: BundleInfo | null
  /** HARD manifest flag: `render.server_only === true`. */
  serverOnly?: boolean
  /** SOFT manifest hint: legacy `project.force_backend`. */
  forceBackendHint?: boolean
  /** Predicted BROWSER render seconds for this mode/params, or null if unknown. */
  estimateSeconds?: number | null
  /** Whether `/api/health` says the server can take work at all. */
  backendAvailable?: boolean
  /** Reason a browser render already failed for this slug this session, if any. */
  lastBrowserFailure?: string | null
}

export interface PlacementDecision {
  placement: Placement
  /**
   * Stable machine-readable reason keys, most significant first. The UI maps
   * the first one to a translated sentence; logs print them all.
   */
  reasons: string[]
  /**
   * True when nothing — not the visitor, not a backend outage — may move this
   * render off the chosen placement. Only the three server-side facts set it.
   */
  hard: boolean
}

/**
 * Seconds of predicted BROWSER render time above which we hand the job to the
 * server instead of making the visitor watch a frozen tab.
 *
 * Scaled by tier because the same predicted number means different things on
 * different machines, and because a `limited` device is exactly the one whose
 * prediction we least trust. `incapable` never reaches this rule.
 */
export const ESTIMATE_THRESHOLD_SECONDS: Record<CapabilityTier, number> = {
  capable: 45,
  limited: 15,
  incapable: 0,
}

/** Whether a cartridge could, in principle, render in a browser at all. */
export function canRenderInBrowser(engine?: string | null): boolean {
  return !BROWSER_INCAPABLE_ENGINES.has(engine ?? '')
}

/**
 * Decide where one render runs.
 *
 * Precedence, highest first — each numbered rule short-circuits:
 *
 *   1. engine ∈ {cadquery, graph, implicit}   -> server, HARD
 *   2. manifest `render.server_only === true`  -> server, HARD
 *   3. bundle unavailable or reports `unsupported` features -> server, HARD
 *   4. `?render=` / `VITE_RENDER_MODE` override
 *   5. user preference `browser` | `server`
 *   6. capability tier `incapable`             -> server
 *   7. a browser render already failed for this slug this session -> server
 *   8. browser estimate > threshold for the tier -> server
 *   9. legacy `force_backend` SOFT hint         -> server ONLY when tier is `limited`
 *  10. default                                  -> BROWSER
 *
 * After the table, one guard: a non-HARD server decision flips back to the
 * browser when the backend is known to be unreachable. A queue we cannot reach
 * is worse than a slow local render.
 */
export function decideRenderPlacement(input: PlacementInput): PlacementDecision {
  const {
    engine = null,
    override = null,
    userPreference = 'auto',
    capabilityTier = 'capable',
    bundle = null,
    serverOnly = false,
    forceBackendHint = false,
    estimateSeconds = null,
    lastBrowserFailure = null,
  } = input
  // `backendAvailable` is deliberately NOT destructured: it is read only by
  // `withOutageGuard(…, input)`, and `input.backendAvailable !== false` already
  // treats an absent value as "assume reachable".

  // 1. No browser kernel exists for this engine. Not negotiable — `?render=wasm`
  //    on a CadQuery cartridge would trade a working render for a certain failure.
  if (!canRenderInBrowser(engine)) {
    return { placement: 'server', reasons: [`engine_unsupported:${engine}`], hard: true }
  }

  // 2. The cartridge author declared server-only. This is the HARD flag that
  //    `force_backend` was being misused as.
  if (serverOnly) {
    return { placement: 'server', reasons: ['manifest_server_only'], hard: true }
  }

  // 3. The bundle is the browser's only source of truth for the cartridge's
  //    files. No bundle, a bundle carrying features this WASM build cannot
  //    execute, or one with an include the server could not resolve, all mean
  //    the browser would produce a wrong model or none at all.
  if (bundle) {
    const unsupported = bundle.unsupported ?? []
    if (unsupported.length > 0) {
      return {
        placement: 'server',
        reasons: [`bundle_unsupported:${unsupported.join(',')}`],
        hard: true,
      }
    }
    const unresolved = bundle.unresolved ?? []
    if (unresolved.length > 0) {
      return {
        placement: 'server',
        reasons: [`bundle_unresolved:${unresolved.join(',')}`],
        hard: true,
      }
    }
    if (bundle.available === false) {
      return { placement: 'server', reasons: ['bundle_unavailable'], hard: true }
    }
  }

  // 4. Explicit operator/support override. Below the hard rules, above everything
  //    a heuristic could say.
  if (override === 'backend') {
    // NOT subject to the outage guard below. `?render=backend` is what support
    // hands a user whose browser is exactly what broke — renders that hang at
    // "Compiling...", die in the WASM kernel, or exhaust the tab. Routing them
    // back to the browser the moment /api/health blips would undo the override
    // at the one moment it matters. They get a clear server error instead.
    return { placement: 'server', reasons: ['override_server'], hard: false }
  }
  if (override === 'wasm') {
    return { placement: 'browser', reasons: ['override_browser'], hard: false }
  }

  // 5. The visitor asked. Honour it — including "server", which usually means
  //    "my laptop is busy and I would rather spend quota than fan noise".
  if (userPreference === 'browser') {
    return { placement: 'browser', reasons: ['preference_browser'], hard: false }
  }
  if (userPreference === 'server') {
    return withOutageGuard({ placement: 'server', reasons: ['preference_server'], hard: false }, input)
  }

  // 6. The machine measured too slow (or has no WebAssembly at all).
  if (capabilityTier === 'incapable') {
    return withOutageGuard({ placement: 'server', reasons: ['capability_incapable'], hard: false }, input)
  }

  // 7. The browser already tried and failed on this cartridge in this session.
  //    Retrying the same failure is not resilience, it is a loop.
  if (lastBrowserFailure) {
    return withOutageGuard(
      { placement: 'server', reasons: [`browser_failed:${lastBrowserFailure}`], hard: false },
      input,
    )
  }

  // 8. Predicted to take longer than this tier tolerates in a browser tab.
  const threshold = ESTIMATE_THRESHOLD_SECONDS[capabilityTier]
  if (
    estimateSeconds !== null
    && Number.isFinite(estimateSeconds)
    && estimateSeconds > threshold
  ) {
    return withOutageGuard(
      {
        placement: 'server',
        reasons: [`estimate_over_threshold:${Math.round(estimateSeconds)}s>${threshold}s`],
        hard: false,
      },
      input,
    )
  }

  // 9. Legacy `force_backend`. Across the commons this flag overwhelmingly
  //    encodes "WASM cannot load our BOSL2 include / our font" — a gap the
  //    wasm-bundle contract closes — not a product preference. It is therefore a
  //    SOFT hint: it only wins on a machine we already judged `limited`.
  if (forceBackendHint && capabilityTier === 'limited') {
    return withOutageGuard(
      { placement: 'server', reasons: ['force_backend_hint_limited_device'], hard: false },
      input,
    )
  }

  // 10. Default: the visitor's own machine, free.
  return { placement: 'browser', reasons: ['default_browser'], hard: false }
}

/**
 * A server placement the visitor cannot reach is not a placement.
 *
 * Applied only to SOFT decisions: the three hard rules mean the browser
 * genuinely cannot produce this model, and a backend outage does not change
 * that — it just means the render fails with a clear server error instead of a
 * confusing WASM one.
 */
function withOutageGuard(decision: PlacementDecision, input: PlacementInput): PlacementDecision {
  if (decision.placement !== 'server') return decision
  if (decision.hard) return decision
  if (input.backendAvailable !== false) return decision
  if (input.capabilityTier === 'incapable') {
    // Nothing works. Stay on the server so the failure names the real problem.
    return { ...decision, reasons: [...decision.reasons, 'backend_unavailable_no_browser_fallback'] }
  }
  return {
    placement: 'browser',
    reasons: ['backend_unavailable', ...decision.reasons],
    hard: false,
  }
}

/** Map a placement back onto the legacy `'backend' | 'wasm'` vocabulary. */
export function placementToLegacyMode(placement: Placement): 'backend' | 'wasm' {
  return placement === 'server' ? 'backend' : 'wasm'
}
