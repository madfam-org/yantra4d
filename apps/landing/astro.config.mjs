import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// Tailwind runs through postcss.config.mjs, which Astro picks up automatically.
// The @astrojs/tailwind integration was dropped on the Astro 7 upgrade: it peers
// on astro ^3||^4||^5 only, and it was already redundant here — it does nothing
// but wire up the same PostCSS plugin this project already configures directly.
// This keeps Tailwind 3 in place, avoiding a Tailwind 4 migration on the public
// marketing site.

// Vendor chunking. Two named chunks, for two different lifetimes:
//
//   vendor-react — react + react-dom + scheduler. Every island needs it, the
//                  ecosystem banner mounts at client:load, so this is paid on
//                  every page view. ~55 KB gzipped.
//   vendor-three — three + @react-three/* (+ the meshopt decoder under
//                  three/examples). Imported dynamically by the 3D stage only,
//                  on the lite/full tiers, once the gallery is in view.
//
// Both are named so the CI budget step and the e2e suite can measure them as
// things rather than guess from hashed filenames. Naming react explicitly is
// not decoration: without it the bundler merged react-dom INTO vendor-three
// (react is a dependency of @react-three/fiber), which made the banner pull
// the whole 3D bundle at load — the exact regression the budgets exist to catch.
const VENDOR_THREE = /node_modules[\\/](three|@react-three)[\\/]/;
const VENDOR_REACT = /node_modules[\\/](react|react-dom|scheduler)[\\/]/;

export default defineConfig({
  integrations: [react()],
  output: 'static',
  i18n: {
    defaultLocale: 'es',
    locales: ['en', 'es'],
    routing: { prefixDefaultLocale: false },
  },
  vite: {
    build: {
      // vendor-three is ~1.1 MB on disk (240 KB brotli) by design and lazy;
      // the budget that matters is enforced in CI on transfer size, not here.
      chunkSizeWarningLimit: 1200,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (VENDOR_THREE.test(id)) return 'vendor-three';
            if (VENDOR_REACT.test(id)) return 'vendor-react';
            return undefined;
          },
        },
      },
    },
  },
});
