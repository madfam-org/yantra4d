import { describe, it, expect } from 'vitest'
import {
  decideRenderPlacement,
  canBrowserEmitFormat,
  BROWSER_EXPORT_FORMATS,
  canRenderInBrowser,
  canRenderAnyModeInBrowser,
  effectiveModeEngine,
  placementToLegacyMode,
  ESTIMATE_THRESHOLD_SECONDS,
} from './renderPlacement'

/**
 * The placement policy, as a table.
 *
 * `decideRenderPlacement` is pure precisely so this can be a table instead of
 * an integration test: every rule gets a row that isolates it, plus a row that
 * proves the rule above it wins. The old `detectMode()` had none of this,
 * which is how `if (API_BASE) return 'backend'` sat above every heuristic in
 * production for as long as it did without a single test noticing.
 */

/** Inputs that, alone, produce the default: a free browser render. */
const BASELINE = {
  engine: 'openscad',
  override: null,
  userPreference: 'auto',
  capabilityTier: 'capable',
  bundle: null,
  exportFormat: null,
  serverOnly: false,
  forceBackendHint: false,
  estimateSeconds: 1,
  backendAvailable: true,
  lastBrowserFailure: null,
}

const decide = (overrides = {}) => decideRenderPlacement({ ...BASELINE, ...overrides })

describe('decideRenderPlacement — the default', () => {
  it('sends an ordinary render to the browser, where it costs nobody anything', () => {
    const d = decide()
    expect(d.placement).toBe('browser')
    expect(d.hard).toBe(false)
    expect(d.reasons).toEqual(['default_browser'])
  })

  it('does not consult the API base at all', () => {
    // The rule this replaces was `if (API_BASE) return 'backend'`, which pinned
    // every production render to the server because production always sets
    // VITE_API_BASE. There is no input for it any more, and that is the point.
    expect(Object.keys(BASELINE)).not.toContain('apiBase')
    expect(decide().placement).toBe('browser')
  })
})

describe('decideRenderPlacement — rule 1: engine', () => {
  for (const engine of ['cadquery', 'graph', 'implicit']) {
    it(`pins ${engine} to the server, hard`, () => {
      const d = decide({ engine })
      expect(d.placement).toBe('server')
      expect(d.hard).toBe(true)
      expect(d.reasons[0]).toBe(`engine_unsupported:${engine}`)
    })

    it(`ignores ?render=wasm on ${engine} — no browser kernel exists`, () => {
      expect(decide({ engine, override: 'wasm' }).placement).toBe('server')
    })

    it(`ignores a browser preference on ${engine}`, () => {
      expect(decide({ engine, userPreference: 'browser' }).placement).toBe('server')
    })
  }

  it('treats a cartridge with no engine field as openscad', () => {
    expect(decide({ engine: null }).placement).toBe('browser')
    expect(decide({ engine: undefined }).placement).toBe('browser')
  })
})

describe('decideRenderPlacement — rule 2: render.server_only', () => {
  it('pins to the server, hard', () => {
    const d = decide({ serverOnly: true })
    expect(d).toMatchObject({ placement: 'server', hard: true })
    expect(d.reasons[0]).toBe('manifest_server_only')
  })

  it('outranks every override and preference', () => {
    expect(decide({ serverOnly: true, override: 'wasm' }).placement).toBe('server')
    expect(decide({ serverOnly: true, userPreference: 'browser' }).placement).toBe('server')
  })

  it('is not implied by force_backend — that flag is only a hint', () => {
    expect(decide({ forceBackendHint: true }).hard).toBe(false)
  })
})

describe('decideRenderPlacement — rule 3: bundle', () => {
  it('pins to the server when the bundle names unsupported features', () => {
    const d = decide({ bundle: { available: true, unsupported: ['import()', 'surface()'] } })
    expect(d).toMatchObject({ placement: 'server', hard: true })
    expect(d.reasons[0]).toBe('bundle_unsupported:import(),surface()')
  })

  it('pins to the server when the bundle reports an unresolved include', () => {
    // A missing include does not make the model look different — it makes the
    // browser render something else entirely, or nothing. Same consequence as
    // an unsupported feature, so the same rule.
    const d = decide({ bundle: { available: true, unresolved: ['projects/x/a.scad: helper.scad'] } })
    expect(d).toMatchObject({ placement: 'server', hard: true })
    expect(d.reasons[0]).toBe('bundle_unresolved:projects/x/a.scad: helper.scad')
  })

  it('unsupported outranks unresolved when both are present', () => {
    const d = decide({ bundle: { available: true, unsupported: ['import()'], unresolved: ['x: y'] } })
    expect(d.reasons[0]).toBe('bundle_unsupported:import()')
  })

  it('pins to the server when the bundle could not be obtained', () => {
    const d = decide({ bundle: { available: false } })
    expect(d).toMatchObject({ placement: 'server', hard: true })
    expect(d.reasons[0]).toBe('bundle_unavailable')
  })

  it('leaves an available, fully-supported bundle on the browser', () => {
    expect(decide({ bundle: { available: true, unsupported: [], unresolved: [] } }).placement).toBe('browser')
  })

  it('does not hold a not-yet-fetched bundle against the browser', () => {
    expect(decide({ bundle: null }).placement).toBe('browser')
  })

  it('outranks the override', () => {
    expect(decide({ bundle: { available: true, unsupported: ['import()'] }, override: 'wasm' }).placement)
      .toBe('server')
  })
})

describe('decideRenderPlacement — rule 4: an export format the browser cannot emit', () => {
  // The browser kernel writes one file, `/output.stl`, and there is no second
  // output path in the worker protocol. Every other format the Studio offers is
  // produced on the server. So this is not a preference, it is arithmetic.
  it('knows the browser makes STL and nothing else', () => {
    expect([...BROWSER_EXPORT_FORMATS]).toEqual(['stl'])
    expect(canBrowserEmitFormat('stl')).toBe(true)
    for (const fmt of ['3mf', 'off', 'obj', 'glb', 'gltf', 'step', 'vrml', 'amf']) {
      expect(canBrowserEmitFormat(fmt)).toBe(false)
    }
  })

  it('treats "no format asked for" as no constraint', () => {
    // An ordinary preview render passes nothing. That must not read as "asked
    // for something the browser cannot do" and quietly meter every render.
    expect(canBrowserEmitFormat(undefined)).toBe(true)
    expect(canBrowserEmitFormat(null)).toBe(true)
    expect(canBrowserEmitFormat('')).toBe(true)
    expect(canBrowserEmitFormat('   ')).toBe(true)
    expect(decide({ exportFormat: null }).placement).toBe('browser')
    expect(decide({ exportFormat: undefined }).placement).toBe('browser')
  })

  it('normalises case and padding before deciding', () => {
    expect(canBrowserEmitFormat('STL')).toBe(true)
    expect(canBrowserEmitFormat(' Stl ')).toBe(true)
    expect(decide({ exportFormat: ' STL ' }).placement).toBe('browser')
    expect(decide({ exportFormat: ' STEP ' }).reasons[0]).toBe('export_format_server_only:step')
  })

  it('sends a step render to the server, HARD, and names the format', () => {
    const d = decide({ exportFormat: 'step' })
    expect(d.placement).toBe('server')
    expect(d.hard).toBe(true)
    expect(d.reasons[0]).toBe('export_format_server_only:step')
  })

  it('keeps an stl render on the free browser path', () => {
    // The common case. `useRender` forwards the export panel's current format
    // on EVERY render, and it defaults to 'stl' — so if this row ever went
    // server the browser default would be dead for the whole product.
    expect(decide({ exportFormat: 'stl' }).placement).toBe('browser')
  })

  it('beats the browser default, the visitor preference and ?render=wasm', () => {
    // Rule ordering, stated as the thing that matters: nothing below rule 4 can
    // ask the kernel for bytes it has no code to write. An override or a
    // preference is a request for a PLACEMENT, not a request to be handed STL
    // under a .step filename.
    expect(decide({ exportFormat: 'step' }).placement).toBe('server')
    expect(decide({ exportFormat: 'step', override: 'wasm' }).placement).toBe('server')
    expect(decide({ exportFormat: 'step', userPreference: 'browser' }).placement).toBe('server')
    expect(decide({ exportFormat: 'step', override: 'wasm', userPreference: 'browser' }))
      .toMatchObject({ placement: 'server', hard: true, reasons: ['export_format_server_only:step'] })
  })

  it('beats the limited-device estimate budget rather than being masked by it', () => {
    // A `limited` device tolerates only 15s in a browser, so a slow cartridge
    // would reach the server anyway — by rule 9, SOFT, which the outage guard
    // can flip back. A format the kernel cannot write must not depend on an
    // estimate happening to be large: it is HARD at any estimate, on any tier.
    const cheapOnCapable = decide({ exportFormat: 'glb', capabilityTier: 'capable', estimateSeconds: 1 })
    expect(cheapOnCapable).toMatchObject({ placement: 'server', hard: true })
    expect(cheapOnCapable.reasons[0]).toBe('export_format_server_only:glb')

    const cheapOnLimited = decide({ exportFormat: 'glb', capabilityTier: 'limited', estimateSeconds: 1 })
    expect(cheapOnLimited).toMatchObject({ placement: 'server', hard: true })
    expect(cheapOnLimited.reasons[0]).toBe('export_format_server_only:glb')
  })

  it('survives a backend outage instead of flipping back to a browser that cannot help', () => {
    // The outage guard exists so a SOFT server decision does not strand a
    // visitor behind an unreachable queue. It must not apply here: the browser
    // would "succeed" and return the wrong bytes, which is worse than an honest
    // server error.
    const d = decide({ exportFormat: '3mf', backendAvailable: false })
    expect(d.placement).toBe('server')
    expect(d.hard).toBe(true)
    expect(d.reasons).toEqual(['export_format_server_only:3mf'])
  })

  it('yields to the cartridge-level hard rules above it', () => {
    // Ordering below the three facts about the cartridge itself. Same answer
    // either way — every hard rule says server — but the REASON should name the
    // most fundamental cause, which is what the badge shows the visitor.
    expect(decide({ exportFormat: 'step', engine: 'cadquery' }).reasons[0])
      .toBe('engine_unsupported:cadquery')
    expect(decide({ exportFormat: 'step', serverOnly: true }).reasons[0])
      .toBe('manifest_server_only')
  })
})

describe('decideRenderPlacement — rule 5: ?render= override', () => {
  it('?render=backend pins the server', () => {
    const d = decide({ override: 'backend' })
    expect(d.placement).toBe('server')
    expect(d.reasons[0]).toBe('override_server')
  })

  it('?render=wasm pins the browser', () => {
    const d = decide({ override: 'wasm' })
    expect(d.placement).toBe('browser')
    expect(d.reasons[0]).toBe('override_browser')
  })

  it('?render=wasm beats an incapable device, a failure and a slow estimate', () => {
    expect(decide({
      override: 'wasm',
      capabilityTier: 'incapable',
      lastBrowserFailure: 'oom',
      estimateSeconds: 9999,
      forceBackendHint: true,
    }).placement).toBe('browser')
  })

  it('?render=backend beats a browser preference', () => {
    expect(decide({ override: 'backend', userPreference: 'browser' }).placement).toBe('server')
  })

  it('?render=backend survives a backend outage — the user asked to stay off WASM', () => {
    // Support hands out ?render=backend precisely when the browser is what
    // broke. Bouncing back to it on a health blip would undo the override at
    // the one moment it matters.
    expect(decide({ override: 'backend', backendAvailable: false }).placement).toBe('server')
  })
})

describe('decideRenderPlacement — rule 6: user preference', () => {
  it('browser wins over an incapable tier, a past failure and a slow estimate', () => {
    expect(decide({
      userPreference: 'browser',
      capabilityTier: 'incapable',
      lastBrowserFailure: 'timeout',
      estimateSeconds: 9999,
    })).toMatchObject({ placement: 'browser', reasons: ['preference_browser'] })
  })

  it('server wins over a capable tier and a cheap estimate', () => {
    expect(decide({ userPreference: 'server' }))
      .toMatchObject({ placement: 'server', reasons: ['preference_server'] })
  })

  it('auto defers to the rules below it', () => {
    expect(decide({ userPreference: 'auto' }).reasons).toEqual(['default_browser'])
  })

  it('a server preference still yields to a backend outage', () => {
    const d = decide({ userPreference: 'server', backendAvailable: false })
    expect(d.placement).toBe('browser')
    expect(d.reasons).toEqual(['backend_unavailable', 'preference_server'])
  })
})

describe('decideRenderPlacement — rule 7: capability tier', () => {
  it('an incapable device goes to the server', () => {
    expect(decide({ capabilityTier: 'incapable' }))
      .toMatchObject({ placement: 'server', hard: false, reasons: ['capability_incapable'] })
  })

  it('a limited device still renders in the browser by default', () => {
    expect(decide({ capabilityTier: 'limited' }).placement).toBe('browser')
  })

  it('an incapable device with the backend down stays on the server, and says so', () => {
    // Nothing works. The failure should name the unreachable server, not blame
    // a browser that was never going to manage it.
    const d = decide({ capabilityTier: 'incapable', backendAvailable: false })
    expect(d.placement).toBe('server')
    expect(d.reasons).toContain('backend_unavailable_no_browser_fallback')
  })
})

describe('decideRenderPlacement — rule 8: a browser render already failed', () => {
  it('routes to the server and names the failure', () => {
    const d = decide({ lastBrowserFailure: 'oom' })
    expect(d.placement).toBe('server')
    expect(d.reasons[0]).toBe('browser_failed:oom')
  })

  it('is overridden by an explicit browser preference', () => {
    expect(decide({ lastBrowserFailure: 'oom', userPreference: 'browser' }).placement).toBe('browser')
  })
})

describe('decideRenderPlacement — rule 9: estimate threshold', () => {
  it('tolerates 45s in a browser on a capable device', () => {
    expect(ESTIMATE_THRESHOLD_SECONDS.capable).toBe(45)
    expect(decide({ estimateSeconds: 45 }).placement).toBe('browser')
    expect(decide({ estimateSeconds: 45.1 }).placement).toBe('server')
  })

  it('tolerates only 15s on a limited device', () => {
    expect(ESTIMATE_THRESHOLD_SECONDS.limited).toBe(15)
    expect(decide({ capabilityTier: 'limited', estimateSeconds: 15 }).placement).toBe('browser')
    expect(decide({ capabilityTier: 'limited', estimateSeconds: 20 }).placement).toBe('server')
    // The same 20s estimate stays in the browser on a capable device.
    expect(decide({ capabilityTier: 'capable', estimateSeconds: 20 }).placement).toBe('browser')
  })

  it('lets the manifest budget (render.browser_max_estimate_seconds) replace the tier default', () => {
    // Tighter than the tier: 30s budget sends a 40s estimate to the server on a capable device.
    expect(decide({ estimateSeconds: 40, browserMaxEstimateSeconds: 30 }).placement).toBe('server')
    expect(decide({ estimateSeconds: 40, browserMaxEstimateSeconds: 30 }).reasons[0])
      .toBe('estimate_over_threshold:40s>30s')
    // Looser than the tier: a 120s budget keeps a 60s estimate in the browser.
    expect(decide({ estimateSeconds: 60, browserMaxEstimateSeconds: 120 }).placement).toBe('browser')
    // Applies on a limited device too (its default is 15s).
    expect(decide({ capabilityTier: 'limited', estimateSeconds: 20, browserMaxEstimateSeconds: 25 }).placement).toBe('browser')
    // Garbage budgets fall back to the tier default.
    expect(decide({ estimateSeconds: 20, browserMaxEstimateSeconds: -1 }).placement).toBe('browser')
    expect(decide({ estimateSeconds: 46, browserMaxEstimateSeconds: Number.NaN }).placement).toBe('server')
    expect(decide({ estimateSeconds: 46, browserMaxEstimateSeconds: null }).placement).toBe('server')
    // 0 is a REAL budget, not a falsy "unset". A `>= 0` test rather than a
    // truthiness test is the whole difference: a cartridge that gives the
    // browser zero seconds sends every render it can estimate to the server,
    // and must not silently inherit the 45 s tier default instead.
    expect(decide({ estimateSeconds: 0.5, browserMaxEstimateSeconds: 0 }).placement).toBe('server')
    expect(decide({ estimateSeconds: 0.5, browserMaxEstimateSeconds: 0 }).reasons[0])
      .toBe('estimate_over_threshold:1s>0s')
    // An estimate of exactly the budget still renders in the browser — the rule
    // is `>`, not `>=`, at every threshold.
    expect(decide({ estimateSeconds: 0, browserMaxEstimateSeconds: 0 }).placement).toBe('browser')
  })

  it('names the numbers in the reason', () => {
    expect(decide({ estimateSeconds: 62.4 }).reasons[0])
      .toBe('estimate_over_threshold:62s>45s')
  })

  it('treats an unknown estimate as no reason to leave the browser', () => {
    expect(decide({ estimateSeconds: null }).placement).toBe('browser')
    expect(decide({ estimateSeconds: NaN }).placement).toBe('browser')
    expect(decide({ estimateSeconds: Infinity }).placement).toBe('browser')
  })
})

describe('decideRenderPlacement — rule 10: force_backend is a SOFT hint', () => {
  it('does NOT move a capable device off the browser', () => {
    // 490 of 501 manifests set this flag, and among the OpenSCAD cartridges it
    // almost always encoded "WASM cannot load our BOSL2 include or our font" —
    // which the wasm-bundle contract now handles. Honouring it unconditionally
    // would keep every one of them on the paid path for no reason.
    expect(decide({ forceBackendHint: true }).placement).toBe('browser')
  })

  it('moves a LIMITED device to the server', () => {
    const d = decide({ forceBackendHint: true, capabilityTier: 'limited' })
    expect(d.placement).toBe('server')
    expect(d.reasons[0]).toBe('force_backend_hint_limited_device')
    expect(d.hard).toBe(false)
  })

  it('yields to an explicit browser preference even on a limited device', () => {
    expect(decide({
      forceBackendHint: true,
      capabilityTier: 'limited',
      userPreference: 'browser',
    }).placement).toBe('browser')
  })

  it('yields to a backend outage', () => {
    const d = decide({ forceBackendHint: true, capabilityTier: 'limited', backendAvailable: false })
    expect(d.placement).toBe('browser')
    expect(d.reasons[0]).toBe('backend_unavailable')
  })
})

describe('decideRenderPlacement — the backend outage guard', () => {
  it('never moves a HARD server decision to the browser', () => {
    for (const hardCase of [
      { engine: 'cadquery' },
      { serverOnly: true },
      { bundle: { available: true, unsupported: ['import()'] } },
      { bundle: { available: false } },
    ]) {
      const d = decide({ ...hardCase, backendAvailable: false })
      expect(d.placement).toBe('server')
      expect(d.hard).toBe(true)
    }
  })

  it('leaves a browser decision untouched', () => {
    expect(decide({ backendAvailable: false }).reasons).toEqual(['default_browser'])
  })
})

describe('canRenderInBrowser', () => {
  it('permits openscad and an unspecified engine', () => {
    expect(canRenderInBrowser('openscad')).toBe(true)
    expect(canRenderInBrowser(null)).toBe(true)
    expect(canRenderInBrowser(undefined)).toBe(true)
  })

  it('refuses the three server-side kernels', () => {
    expect(canRenderInBrowser('cadquery')).toBe(false)
    expect(canRenderInBrowser('graph')).toBe(false)
    expect(canRenderInBrowser('implicit')).toBe(false)
  })
})

describe('placementToLegacyMode', () => {
  it('maps onto the vocabulary the rest of the app still speaks', () => {
    expect(placementToLegacyMode('browser')).toBe('wasm')
    expect(placementToLegacyMode('server')).toBe('backend')
  })
})


describe('effectiveModeEngine — engine is a MODE property', () => {
  // Mirrors ProjectManifest.mode_engine() in apps/api/manifest.py. Getting this
  // wrong is expensive in one specific way: `soft-jaw` declares
  // `project.engine: "cadquery"` and then a mode with `engine: "openscad"`.
  // Reading the project engine alone would send that mode to the metered path
  // forever — and 19 cartridges in the commons are dual-engine.
  //
  // The fixture named gridfinity until 2026-09-04; gridfinity is CadQuery-only
  // now (its OpenSCAD side left the commons), so it can no longer illustrate
  // the mixed case. Shape follows projects/soft-jaw/project.json.
  const softJaw = {
    engine: 'cadquery',
    modes: [
      { id: 'jaw', scad_file: 'main.py' },
      { id: 'jaw_pair', scad_file: 'main.py' },
      { id: 'vee_jaw', scad_file: 'main.py' },
      { id: 'jaw_body', engine: 'openscad', scad_file: 'soft_jaw.scad' },
    ],
  }

  it("an explicit mode engine wins over the project's", () => {
    expect(effectiveModeEngine(softJaw, 'jaw_body')).toBe('openscad')
  })

  it('infers cadquery from a .py or .cq scad_file', () => {
    expect(effectiveModeEngine(softJaw, 'jaw')).toBe('cadquery')
    expect(effectiveModeEngine({ engine: 'openscad', modes: [{ id: 'm', scad_file: 'part.cq' }] }, 'm'))
      .toBe('cadquery')
  })

  it('infers graph from a .graph.json scad_file', () => {
    expect(effectiveModeEngine({ engine: 'openscad', modes: [{ id: 'm', scad_file: 'flow.graph.json' }] }, 'm'))
      .toBe('graph')
  })

  it('falls back to the project engine when nothing else decides', () => {
    expect(effectiveModeEngine({ engine: 'cadquery', modes: [{ id: 'm', scad_file: 'a.scad' }] }, 'm'))
      .toBe('cadquery')
    expect(effectiveModeEngine({ modes: [{ id: 'm', scad_file: 'a.scad' }] }, 'm')).toBe('openscad')
  })

  it('defaults an absent project engine to openscad', () => {
    expect(effectiveModeEngine(null, null)).toBe('openscad')
    expect(effectiveModeEngine({}, 'nope')).toBe('openscad')
    expect(effectiveModeEngine({ engine: 'nonsense' }, null)).toBe('openscad')
  })

  it('ignores an unknown engine on a mode and keeps inferring', () => {
    expect(effectiveModeEngine({ engine: 'openscad', modes: [{ id: 'm', engine: 'wat', scad_file: 'a.py' }] }, 'm'))
      .toBe('cadquery')
  })

  it('makes every mode implicit for an implicit project — no exceptions', () => {
    // Implicit fields are a whole-project concern; a per-mode override would
    // mean rendering half a hyperobject with the wrong kernel.
    const implicit = { engine: 'implicit', modes: [{ id: 'm', engine: 'openscad', scad_file: 'a.scad' }] }
    expect(effectiveModeEngine(implicit, 'm')).toBe('implicit')
    expect(effectiveModeEngine(implicit, null)).toBe('implicit')
  })

  it('falls back to the project engine for a mode id that does not exist', () => {
    expect(effectiveModeEngine(softJaw, 'ghost')).toBe('cadquery')
    expect(effectiveModeEngine(softJaw, null)).toBe('cadquery')
  })
})

describe('canRenderAnyModeInBrowser', () => {
  it('is true for a dual-engine cartridge with at least one OpenSCAD mode', () => {
    expect(canRenderAnyModeInBrowser({
      engine: 'cadquery',
      modes: [{ id: 'jaw', scad_file: 'main.py' }, { id: 'jaw_body', engine: 'openscad', scad_file: 'soft_jaw.scad' }],
    })).toBe(true)
  })

  it('is false when every mode runs a server-side kernel', () => {
    expect(canRenderAnyModeInBrowser({
      engine: 'cadquery',
      modes: [{ id: 'jaw', scad_file: 'main.py' }, { id: 'vee_jaw', scad_file: 'main.py' }],
    })).toBe(false)
  })

  it('falls back to the project engine when the manifest lists no modes', () => {
    expect(canRenderAnyModeInBrowser({ engine: 'openscad' })).toBe(true)
    expect(canRenderAnyModeInBrowser({ engine: 'graph' })).toBe(false)
    expect(canRenderAnyModeInBrowser(null)).toBe(true)
  })
})

describe('decideRenderPlacement — per-mode engine in practice', () => {
  // The end-to-end consequence of effectiveModeEngine, expressed as placements.
  const softJaw = {
    engine: 'cadquery',
    modes: [
      { id: 'jaw', scad_file: 'main.py' },
      { id: 'jaw_body', engine: 'openscad', scad_file: 'soft_jaw.scad' },
    ],
  }

  it("soft-jaw's OpenSCAD mode renders in the browser, for free", () => {
    expect(decide({ engine: effectiveModeEngine(softJaw, 'jaw_body') }).placement).toBe('browser')
  })

  it("soft-jaw's CadQuery mode stays hard-pinned to the server", () => {
    const d = decide({ engine: effectiveModeEngine(softJaw, 'jaw') })
    expect(d).toMatchObject({ placement: 'server', hard: true })
  })
})
