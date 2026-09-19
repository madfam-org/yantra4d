/**
 * Tier access for islands and page scripts. The decision itself lives in
 * `tier-core.js` (pure, shared with the inline <head> bootstrap); this module
 * adds the two things that need a live browser: the WebGL probe that runs right
 * before the 3D chunk would load, and persistence of the visitor's choice.
 *
 * The probe can only DEMOTE. The bootstrap decides from cheap signals and
 * writes nothing; a tier is stored only once it has been measured
 * (`probed: true`) or chosen (`user: true`) — an unmeasured guess must not
 * masquerade as a probe result on the next visit.
 */
import {
  TIER_STORAGE_KEY,
  TIER_VERSION,
  classifyTier,
  lowerTier,
  parseStoredTier,
  parseTierOverride,
  readCheapSignals,
} from './tier-core.js';

export type Tier = 'still' | 'lite' | 'full';
export type TierSource = 'override' | 'user' | 'stored' | 'signals' | 'probe' | 'error' | 'markup';

export interface TierState {
  tier: Tier;
  source: TierSource;
}

export interface WebglProbe {
  /** A WebGL2 context could be created. */
  webgl2: boolean;
  /** The only context available is software-rasterized. */
  softwareRenderer: boolean;
  /** Unmasked renderer string when the browser exposes it; null otherwise. */
  renderer: string | null;
}

export const TIER_CHANGE_EVENT = 'y4d:tier-change';

const SOFTWARE_RE =
  /swiftshader|llvmpipe|softpipe|software rasterizer|microsoft basic render|mesa offscreen|virtualbox|vmware svga/i;

function root(): HTMLElement | null {
  return typeof document !== 'undefined' ? document.documentElement : null;
}

function safeGet(key: string): string | null {
  try {
    return globalThis.localStorage?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string | null): void {
  try {
    if (value === null) globalThis.localStorage?.removeItem(key);
    else globalThis.localStorage?.setItem(key, value);
  } catch {
    /* private mode / quota — the tier still works for this page load */
  }
}

/** The tier the page is currently rendering, as the <head> bootstrap left it. */
export function currentTier(): TierState {
  const el = root();
  const tier = el?.getAttribute('data-tier');
  const source = (el?.getAttribute('data-tier-source') as TierSource | null) ?? 'markup';
  if (tier === 'still' || tier === 'lite' || tier === 'full') return { tier, source };
  return { tier: 'still', source: 'markup' };
}

function applyTier(tier: Tier, source: TierSource): TierState {
  const el = root();
  if (el) {
    el.setAttribute('data-tier', tier);
    el.setAttribute('data-tier-source', source);
  }
  const state = { tier, source };
  try {
    globalThis.dispatchEvent?.(new CustomEvent(TIER_CHANGE_EVENT, { detail: state }));
  } catch {
    /* no CustomEvent (very old engine) — nothing subscribes there anyway */
  }
  return state;
}

/**
 * Create a WebGL2 context the way the stage will, and release it.
 *
 * `failIfMajorPerformanceCaveat: true` is the honest question: it refuses to
 * hand back a context that would run on a CPU rasterizer. If that refuses and
 * a plain request succeeds, the machine has WebGL but no GPU behind it — a
 * `still` device, whatever its core count says.
 */
export function probeWebgl(doc: Document | undefined = typeof document !== 'undefined' ? document : undefined): WebglProbe {
  if (!doc) return { webgl2: false, softwareRenderer: false, renderer: null };
  let canvas: HTMLCanvasElement;
  try {
    canvas = doc.createElement('canvas');
  } catch {
    return { webgl2: false, softwareRenderer: false, renderer: null };
  }
  const tryContext = (caveat: boolean): WebGL2RenderingContext | null => {
    try {
      const gl = canvas.getContext('webgl2', {
        failIfMajorPerformanceCaveat: caveat,
        powerPreference: 'default',
      });
      return gl && typeof (gl as WebGL2RenderingContext).getParameter === 'function'
        ? (gl as WebGL2RenderingContext)
        : null;
    } catch {
      return null;
    }
  };

  let gl = tryContext(true);
  let softwareRenderer = false;
  if (!gl) {
    gl = tryContext(false);
    if (!gl) return { webgl2: false, softwareRenderer: false, renderer: null };
    softwareRenderer = true;
  }

  let renderer: string | null = null;
  try {
    const info = gl.getExtension('WEBGL_debug_renderer_info');
    if (info) {
      const value = gl.getParameter(info.UNMASKED_RENDERER_WEBGL);
      renderer = typeof value === 'string' ? value : null;
    }
  } catch {
    renderer = null;
  }
  if (renderer && SOFTWARE_RE.test(renderer)) softwareRenderer = true;

  try {
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  } catch {
    /* best effort — the canvas is unreferenced after this anyway */
  }
  return { webgl2: true, softwareRenderer, renderer };
}

/**
 * Settle the tier before loading 3D: keep an override or a chosen/measured
 * record as is; otherwise probe WebGL, classify with the full signal set and
 * store the measured answer. Returns the (possibly demoted) tier.
 *
 * Idempotent and cheap after the first call: a fresh stored record short-circuits.
 */
export function settleTier(now: number = Date.now()): TierState {
  const current = currentTier();
  if (current.source === 'override' || current.source === 'user') return current;

  const stored = parseStoredTier(safeGet(TIER_STORAGE_KEY), now);
  if (stored && (stored.probed || stored.user)) {
    return applyTier(stored.tier as Tier, stored.user ? 'user' : 'stored');
  }

  const signals = readCheapSignals(globalThis as unknown as Window);
  const probe = probeWebgl();
  const measured = classifyTier({ ...signals, webgl2: probe.webgl2, softwareRenderer: probe.softwareRenderer }) as Tier;
  // The bootstrap's answer is the ceiling; the measurement can only lower it.
  const tier = lowerTier(current.tier, measured) as Tier;

  safeSet(
    TIER_STORAGE_KEY,
    JSON.stringify({ version: TIER_VERSION, tier, at: now, probed: true, renderer: probe.renderer }),
  );
  return applyTier(tier, tier === current.tier ? current.source : 'probe');
}

/**
 * The visitor's explicit choice. `null` returns to automatic. A choice never
 * expires and wins over measurements (never over `?tier=`, which is QA's).
 */
export function setUserTier(tier: Tier | null, now: number = Date.now()): void {
  if (tier === null) {
    safeSet(TIER_STORAGE_KEY, null);
    return;
  }
  safeSet(TIER_STORAGE_KEY, JSON.stringify({ version: TIER_VERSION, tier, at: now, user: true }));
}

/** Whether the current tier is a visitor's choice (drives the toggle's label). */
export function userChoseTier(now: number = Date.now()): Tier | null {
  const stored = parseStoredTier(safeGet(TIER_STORAGE_KEY), now);
  return stored && stored.user ? (stored.tier as Tier) : null;
}

export { parseTierOverride, classifyTier, TIER_STORAGE_KEY };
