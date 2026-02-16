/** Centralized environment URLs — single source of truth for local vs production. */
export const STUDIO_URL = import.meta.env.DEV
  ? 'http://localhost:5173'
  : 'https://4d-app.madfam.io';

export const API_URL = import.meta.env.DEV
  ? 'http://localhost:5000'
  : 'https://4d-api.madfam.io';
