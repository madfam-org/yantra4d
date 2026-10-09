/**
 * Device tier for the landing: which rendering experience a visitor gets.
 *
 *   still — posters and CSS only. Zero 3D bytes. What crawlers, no-WebGL
 *           browsers, reduced-motion / save-data visitors and very small
 *           devices get. Also the no-JS default (the <html> element ships with
 *           data-tier="still" and this code only ever UPGRADES it).
 *   lite  — one light 3D scene, device pixel ratio 1, no post-processing.
 *   full  — the immersive stage.
 *
 * THIS FILE IS EVALUATED TWICE, DELIBERATELY. Once as an ES module (imported by
 * `tier.ts` and the tests), and once INLINE in <head> before first paint
 * (BaseLayout strips the `export ` keywords and injects the text, followed by
 * `tier-inline.js`). That is why it uses no imports, no optional chaining, no
 * `??`, no template literals and no top-level names that could collide with
 * browser globals: a syntax error in an old engine must fail closed to `still`,
 * not take the page down. `tier.test.ts` pins the two evaluations to the same
 * answers.
 *
 * UNKNOWN IS UNKNOWN. A signal the browser withholds never demotes a device.
 * `deviceMemory` does not exist on Firefox or Safari; absent means "we do not
 * know", not "4 GB". Same discipline as the Studio's renderCapability.ts.
 */

export var TIER_VERSION = 1;
export var TIER_STORAGE_KEY = 'y4d.landing_tier.v1';
/** A measured record is trusted for a week: hardware does not change, browsers do. */
export var TIER_TTL_MS = 7 * 24 * 60 * 60 * 1000;
export var TIERS = ['still', 'lite', 'full'];

/**
 * Renderer strings that mean "no GPU behind this context". Read only when the
 * browser exposes WEBGL_debug_renderer_info (Chromium does; Firefox and Safari
 * mask it, which is fine — `failIfMajorPerformanceCaveat` catches the same
 * case without the string).
 */
export var SOFTWARE_RENDERER_RE =
  /swiftshader|llvmpipe|softpipe|software rasterizer|microsoft basic render|mesa offscreen|virtualbox|vmware svga/i;

/**
 * Crawlers and headless agents get `still`: the page's facts are all HTML, the
 * stage is decoration. Headless Chrome is listed on purpose — Lighthouse and
 * Playwright pass `?tier=` explicitly when they mean to measure a 3D tier.
 */
export var BOT_UA_RE =
  /bot|crawl|spider|slurp|headlesschrome|lighthouse|pagespeed|prerender|facebookexternalhit|embedly|linkedinbot|pinterest|whatsapp|telegrambot|discordbot|w3c_validator/i;

/**
 * The classifier. PURE — every input is passed in.
 *
 * Rules, in order (first match wins for `still`; the rest only lower to `lite`):
 *   - webgl2 known false                       -> still  (nothing to render with)
 *   - software renderer known true             -> still  (a CPU pretending to be a GPU)
 *   - prefers-reduced-motion                   -> still  (the stage is motion)
 *   - Save-Data / prefers-reduced-data         -> still  (the 3D chunk is a download they declined)
 *   - bot / headless UA                        -> still
 *   - deviceMemory KNOWN and < 2 GB            -> still
 *   - hardwareConcurrency KNOWN and < 2        -> still
 *   - mobile                                   -> lite   (battery and thermals, not just speed)
 *   - hardwareConcurrency KNOWN and < 4        -> lite
 *   - deviceMemory KNOWN and < 4 GB            -> lite
 *   - everything else, INCLUDING unknowns      -> full
 *
 * @param {TierSignals} s
 * @returns {'still'|'lite'|'full'}
 */
export function classifyTier(s) {
  s = s || {};
  if (s.webgl2 === false) return 'still';
  if (s.softwareRenderer === true) return 'still';
  if (s.reducedMotion === true) return 'still';
  if (s.reducedData === true) return 'still';
  if (s.bot === true) return 'still';
  if (typeof s.memoryGb === 'number' && s.memoryGb < 2) return 'still';
  if (typeof s.cores === 'number' && s.cores < 2) return 'still';
  var tier = 'full';
  if (s.mobile === true) tier = 'lite';
  if (typeof s.cores === 'number' && s.cores < 4) tier = 'lite';
  if (typeof s.memoryGb === 'number' && s.memoryGb < 4) tier = 'lite';
  return tier;
}

/** The lower of two tiers — a probe can only ever demote. */
export function lowerTier(a, b) {
  return TIERS.indexOf(a) <= TIERS.indexOf(b) ? a : b;
}

/**
 * `?tier=still|lite|full` — the QA and support override. Wins over everything,
 * is never persisted. Anything else is ignored rather than coerced.
 * @param {string} search
 * @returns {'still'|'lite'|'full'|null}
 */
export function parseTierOverride(search) {
  var m = /(?:^\?|[?&])tier=(still|lite|full)(?:&|$)/i.exec(String(search || ''));
  return m ? m[1].toLowerCase() : null;
}

/**
 * A stored record, or null when it is absent, malformed, from another version,
 * or (for measured records) older than the TTL. A record the visitor chose
 * (`user: true`) never expires — it is a preference, not a measurement.
 * @param {string|null} raw
 * @param {number} now
 */
export function parseStoredTier(raw, now) {
  if (!raw) return null;
  var r;
  try {
    r = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!r || typeof r !== 'object') return null;
  if (r.version !== TIER_VERSION) return null;
  if (TIERS.indexOf(r.tier) < 0) return null;
  if (typeof r.at !== 'number') return null;
  if (!r.user && now - r.at > TIER_TTL_MS) return null;
  return r;
}

/**
 * The signals that cost nothing to read. WebGL is NOT probed here — creating a
 * context in <head> spins up the GPU process on some devices and delays first
 * paint; `tier.ts` probes it later, right before the 3D chunk would load, and
 * can only demote. Both WebGL fields are therefore `null` (unknown) here.
 * @param {Window} win
 * @returns {TierSignals}
 */
export function readCheapSignals(win) {
  var nav = (win && win.navigator) || {};
  var ua = typeof nav.userAgent === 'string' ? nav.userAgent : '';

  var mobile = null;
  if (nav.userAgentData && typeof nav.userAgentData.mobile === 'boolean') {
    mobile = nav.userAgentData.mobile;
  } else if (ua) {
    mobile = /Android|iPhone|iPad|iPod|Mobile|Silk|Kindle|Opera Mini/i.test(ua);
  }

  var cores = null;
  if (typeof nav.hardwareConcurrency === 'number' && isFinite(nav.hardwareConcurrency) && nav.hardwareConcurrency > 0) {
    cores = nav.hardwareConcurrency;
  }
  var memoryGb = null;
  if (typeof nav.deviceMemory === 'number' && isFinite(nav.deviceMemory) && nav.deviceMemory > 0) {
    memoryGb = nav.deviceMemory;
  }

  var reducedMotion = false;
  var reducedData = false;
  try {
    if (win && typeof win.matchMedia === 'function') {
      reducedMotion = win.matchMedia('(prefers-reduced-motion: reduce)').matches === true;
      reducedData = win.matchMedia('(prefers-reduced-data: reduce)').matches === true;
    }
  } catch {
    /* jsdom and old engines throw on unknown features */
  }
  if (nav.connection && nav.connection.saveData === true) reducedData = true;

  return {
    webgl2: null,
    softwareRenderer: null,
    reducedMotion: reducedMotion,
    reducedData: reducedData,
    bot: ua ? BOT_UA_RE.test(ua) : false,
    memoryGb: memoryGb,
    cores: cores,
    mobile: mobile,
  };
}

/**
 * Override > stored record > cheap signals. PURE. Returns the tier and where it
 * came from, so the page can say so (and the RUM beacon can count it).
 * @param {{search?: string, storedRaw?: string|null, now?: number, signals?: TierSignals}} input
 */
export function resolveTier(input) {
  input = input || {};
  var override = parseTierOverride(input.search || '');
  if (override) return { tier: override, source: 'override' };
  var stored = parseStoredTier(input.storedRaw || null, typeof input.now === 'number' ? input.now : 0);
  if (stored) return { tier: stored.tier, source: stored.user ? 'user' : 'stored' };
  return { tier: classifyTier(input.signals || {}), source: 'signals' };
}

/**
 * @typedef {Object} TierSignals
 * @property {boolean|null} webgl2 a WebGL2 context could be created (null = not probed)
 * @property {boolean|null} softwareRenderer the context is software-rasterized (null = not probed)
 * @property {boolean} reducedMotion prefers-reduced-motion: reduce
 * @property {boolean} reducedData prefers-reduced-data: reduce, or connection.saveData
 * @property {boolean} bot crawler / headless user agent
 * @property {number|null} memoryGb navigator.deviceMemory, null when withheld (NOT 4)
 * @property {number|null} cores navigator.hardwareConcurrency, null when withheld
 * @property {boolean|null} mobile userAgentData.mobile or a UA fallback, null when unreadable
 */
