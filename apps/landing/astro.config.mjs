import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// Tailwind runs through postcss.config.mjs, which Astro picks up automatically.
// The @astrojs/tailwind integration was dropped on the Astro 7 upgrade: it peers
// on astro ^3||^4||^5 only, and it was already redundant here — it does nothing
// but wire up the same PostCSS plugin this project already configures directly.
// This keeps Tailwind 3 in place, avoiding a Tailwind 4 migration on the public
// marketing site.
export default defineConfig({
  integrations: [react()],
  output: 'static',
  i18n: {
    defaultLocale: 'es',
    locales: ['en', 'es'],
    routing: { prefixDefaultLocale: false },
  },
});
