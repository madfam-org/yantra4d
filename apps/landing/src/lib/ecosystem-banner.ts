import { STORAGE_KEY, BANNER_VERSION, DISMISS_DAYS } from '../components/vendor/ecosystem-banner/presentation';
import { ecosystemLink, type EcosystemLink } from '../components/vendor/ecosystem-banner/links';
import {
  DEFAULT_ECOSYSTEM_PLATFORMS,
  MADFAM_OWNED_DOMAINS,
  type EcosystemPlatform,
} from '../components/vendor/ecosystem-banner/platforms';

export type EcosystemBannerEntry = EcosystemPlatform & EcosystemLink;

/**
 * The banner's links under the own-site policy (`vendor/ecosystem-banner/links.ts`).
 *
 * The banner is static HTML, rendered at build time, so the origin host is this
 * site's canonical host (`SITE_ORIGIN`), passed in by `EcosystemBanner.astro`,
 * not `window.location`. An own MADFAM destination gets `rel="noopener"` and
 * `utm_source=<origin>&utm_medium=ecosystem&utm_campaign=banner`; a third-party
 * one keeps `rel="noopener noreferrer"`; the link to this site itself and every
 * link built without a public origin (dev) stay untagged.
 */
export function ecosystemBannerEntries(
  originHost: string | undefined,
  platforms: readonly EcosystemPlatform[] = DEFAULT_ECOSYSTEM_PLATFORMS,
): EcosystemBannerEntry[] {
  return platforms
    .filter((p) => p.keyword && p.name && p.url)
    .map((p) => ({
      ...p,
      ...ecosystemLink(p.url, { surface: 'banner', originHost, ownedDomains: MADFAM_OWNED_DOMAINS }),
    }));
}

/** Wire the static banner without loading an island runtime. */
export function wireEcosystemBanner(banner: HTMLElement) {
  let dismissed = false;
  try {
    const record = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    dismissed = record?.v === BANNER_VERSION
      && typeof record.dismissed_at === 'number'
      && Date.now() - record.dismissed_at < DISMISS_DAYS * 86400000;
  } catch { /* Storage may be unavailable; the session can still dismiss. */ }
  banner.hidden = dismissed;
  banner.querySelector('button')?.addEventListener('click', () => {
    banner.hidden = true;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ v: BANNER_VERSION, dismissed_at: Date.now() }));
    } catch { /* Session-only dismissal. */ }
  });
}
