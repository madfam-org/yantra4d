/**
 * One first-party beacon per session: which tier the page decided, and why.
 *
 * Cloudflare Web Analytics (see BaseLayout) measures the vitals; it cannot see
 * the tier, so this beacon carries that. No identifier, no email, no cookie —
 * the payload is the tier, its source and the page's language, nothing that
 * distinguishes a visitor (the attribution contract: never an email or a
 * Janua subject).
 *
 * OFF unless the build sets `PUBLIC_RUM_BEACON=1`: the analytics endpoint has
 * to accept the `landing_tier` event first (an API change that ships
 * separately), and a beacon the server rejects is just noise.
 */
import { currentTier } from './tier';

export const RUM_EVENT = 'landing_tier';
export const RUM_SESSION_KEY = 'y4d.landing_rum.v1';

export interface TierBeacon {
  project: 'landing';
  event: typeof RUM_EVENT;
  data: { tier: string; source: string; lang: string; path: string };
}

export function buildTierBeacon(doc: Document = document): TierBeacon {
  const { tier, source } = currentTier();
  return {
    project: 'landing',
    event: RUM_EVENT,
    data: {
      tier,
      source,
      lang: doc.documentElement.lang || 'es',
      path: doc.location?.pathname ?? '/',
    },
  };
}

export interface SendOptions {
  endpoint: string;
  enabled: boolean;
  storage?: Storage | null;
  send?: (url: string, body: string) => boolean;
}

/**
 * Send the beacon once per browser session. Returns true when a beacon was
 * handed to the browser. Never throws: analytics must not break a page.
 */
export function sendTierBeacon({ endpoint, enabled, storage, send }: SendOptions): boolean {
  if (!enabled) return false;
  try {
    const store = storage === undefined ? globalThis.sessionStorage : storage;
    if (store?.getItem(RUM_SESSION_KEY)) return false;
    const body = JSON.stringify(buildTierBeacon());
    const transport =
      send ??
      ((url: string, payload: string) =>
        typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function'
          ? navigator.sendBeacon(url, new Blob([payload], { type: 'application/json' }))
          : false);
    const ok = transport(endpoint, body);
    if (ok) store?.setItem(RUM_SESSION_KEY, '1');
    return ok;
  } catch {
    return false;
  }
}
