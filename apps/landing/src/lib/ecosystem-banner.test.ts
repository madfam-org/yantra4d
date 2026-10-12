import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ecosystemBannerEntries, wireEcosystemBanner } from './ecosystem-banner';
import { BANNER_VERSION, STORAGE_KEY } from '../components/vendor/ecosystem-banner/presentation';
import { ecosystemLink, isOwnHost } from '../components/vendor/ecosystem-banner/links';
import {
  DEFAULT_ECOSYSTEM_PLATFORMS,
  MADFAM_OWNED_DOMAINS,
} from '../components/vendor/ecosystem-banner/platforms';

describe('static ecosystem banner', () => {
  beforeEach(() => { localStorage.clear(); document.body.innerHTML = ''; vi.restoreAllMocks(); });
  const mount = () => {
    document.body.innerHTML = '<aside hidden><button>Dismiss</button></aside>';
    const banner = document.querySelector('aside')!;
    wireEcosystemBanner(banner);
    return banner;
  };
  it('shows the banner and persists its dismissal across page loads', () => {
    const banner = mount();
    expect(banner.hidden).toBe(false);
    banner.querySelector('button')!.click();
    expect(banner.hidden).toBe(true);
    expect(mount().hidden).toBe(true);
  });
  it.each([
    { v: BANNER_VERSION - 1, dismissed_at: Date.now() },
    { v: BANNER_VERSION, dismissed_at: Date.now() - 31 * 86400000 },
    { v: BANNER_VERSION, dismissed_at: 'yesterday' },
    null,
  ])('shows expired or invalid records: %j', record => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
    expect(mount().hidden).toBe(false);
  });
  it('survives malformed or unavailable storage and still dismisses', () => {
    localStorage.setItem(STORAGE_KEY, 'invalid');
    expect(mount().hidden).toBe(false);
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('disabled'); });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('disabled'); });
    const banner = mount();
    expect(banner.hidden).toBe(false);
    banner.querySelector('button')!.click();
    expect(banner.hidden).toBe(true);
  });
});

describe('ecosystem banner links (2026-10-11 fix)', () => {
  it('links Forgesight to forgesight.app, never the retired forgesight.quest', () => {
    const urls = DEFAULT_ECOSYSTEM_PLATFORMS.map((p) => p.url);
    expect(urls).toContain('https://forgesight.app');
    expect(urls.some((u) => u.includes('forgesight.quest'))).toBe(false);
  });

  it('treats every default ticker destination as a MADFAM-owned host', () => {
    for (const p of DEFAULT_ECOSYSTEM_PLATFORMS) {
      expect(isOwnHost(new URL(p.url).hostname, MADFAM_OWNED_DOMAINS)).toBe(true);
    }
  });

  it('tags an own-site link with rel=noopener and the ecosystem UTM set', () => {
    const link = ecosystemLink('https://forgesight.app', {
      surface: 'banner',
      originHost: 'www.karafiel.mx',
      ownedDomains: MADFAM_OWNED_DOMAINS,
    });
    expect(link.rel).toBe('noopener');
    const url = new URL(link.href);
    expect(url.hostname).toBe('forgesight.app');
    expect(url.searchParams.get('utm_source')).toBe('karafiel.mx');
    expect(url.searchParams.get('utm_medium')).toBe('ecosystem');
    expect(url.searchParams.get('utm_campaign')).toBe('banner');
  });

  it('adds no UTM on the same host or from localhost', () => {
    for (const originHost of ['forgesight.app', 'localhost', '127.0.0.1', undefined]) {
      expect(
        ecosystemLink('https://forgesight.app', {
          surface: 'banner',
          originHost,
          ownedDomains: MADFAM_OWNED_DOMAINS,
        }),
      ).toEqual({ href: 'https://forgesight.app', rel: 'noopener' });
    }
  });

  it('keeps noreferrer and adds no UTM on a third-party link', () => {
    expect(
      ecosystemLink('https://github.com/madfam-org', {
        surface: 'banner',
        originHost: 'karafiel.mx',
        ownedDomains: MADFAM_OWNED_DOMAINS,
      }),
    ).toEqual({ href: 'https://github.com/madfam-org', rel: 'noopener noreferrer' });
  });
});

describe('ecosystemBannerEntries (what EcosystemBanner.astro renders)', () => {
  it('tags every other MADFAM site with utm_source=yantra4d.com and leaves Yantra4D itself bare', () => {
    const entries = ecosystemBannerEntries('yantra4d.com');
    expect(entries).toHaveLength(DEFAULT_ECOSYSTEM_PLATFORMS.length);
    for (const entry of entries) {
      expect(entry.rel).toBe('noopener');
      const url = new URL(entry.href);
      if (url.hostname === 'yantra4d.com') {
        expect(entry.href).toBe('https://yantra4d.com');
        continue;
      }
      expect(url.searchParams.get('utm_source')).toBe('yantra4d.com');
      expect(url.searchParams.get('utm_medium')).toBe('ecosystem');
      expect(url.searchParams.get('utm_campaign')).toBe('banner');
    }
    const forgesight = entries.find((e) => e.name === 'Forge Sight')!;
    expect(new URL(forgesight.href).hostname).toBe('forgesight.app');
  });

  it('renders untagged own-site links when there is no public origin (dev build)', () => {
    for (const entry of ecosystemBannerEntries(undefined)) {
      expect(entry).toMatchObject({ href: entry.url, rel: 'noopener' });
    }
  });

  it('keeps noreferrer and the bare URL on a third-party platform', () => {
    const [entry] = ecosystemBannerEntries('yantra4d.com', [
      { keyword: 'CODE', name: 'GitHub', url: 'https://github.com/madfam-org' },
    ]);
    expect(entry).toMatchObject({ href: 'https://github.com/madfam-org', rel: 'noopener noreferrer' });
  });
});
