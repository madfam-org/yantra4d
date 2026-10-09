import { STORAGE_KEY, BANNER_VERSION, DISMISS_DAYS } from '../components/vendor/ecosystem-banner/presentation';

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
