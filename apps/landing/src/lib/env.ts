/** Centralized environment URLs — single source of truth for local vs production.
 *  Uses runtime hostname check so locally-built sites still point to local services. */
const isLocal = import.meta.env.DEV || (typeof window !== 'undefined'
  && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'));

export const STUDIO_URL = import.meta.env.PUBLIC_STUDIO_URL || (isLocal
  ? 'http://localhost:5173'
  : 'https://4d-app.madfam.io');

export const API_URL = isLocal
  ? 'http://localhost:5000'
  : 'https://4d-api.madfam.io';
