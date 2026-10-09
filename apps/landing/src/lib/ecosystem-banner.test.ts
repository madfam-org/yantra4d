import { beforeEach, describe, expect, it, vi } from 'vitest';
import { wireEcosystemBanner } from './ecosystem-banner';
import { BANNER_VERSION, STORAGE_KEY } from '../components/vendor/ecosystem-banner/presentation';

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
