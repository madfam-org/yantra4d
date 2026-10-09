/** Centralized environment URLs — single source of truth for local vs production.
 *  Uses runtime hostname check so locally-built sites still point to local services. */
const isLocal = import.meta.env.DEV || (typeof window !== 'undefined'
  && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'));

export const STUDIO_URL = import.meta.env.PUBLIC_STUDIO_URL || (isLocal
  ? 'http://localhost:5173'
  : 'https://app.yantra4d.com');

export const API_URL = isLocal
  ? 'http://localhost:5000'
  : 'https://api.yantra4d.com';

/** The public origin of this site, for canonical / alternate / Open Graph URLs.
 *  Build-time only (Astro `site` is not configured); never derived from the
 *  request so a preview build cannot mint canonical links to itself. */
export const SITE_ORIGIN = import.meta.env.PUBLIC_SITE_ORIGIN || 'https://yantra4d.com';
