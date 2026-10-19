/* global process */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'
import fs from 'fs'
import path from 'path'
import {
  DEFAULT_STUDIO_ORIGIN,
  buildLlms,
  buildRobots,
  buildSitemap,
  catalogSlugs,
} from './src/lib/crawlFiles.js'

// Custom plugin to keep fallback manifest continuously in sync with the flagship project (Gridfinity)
function writeFallbackManifest(src, dest) {
  const manifestText = fs
    .readFileSync(src, 'utf8')
    .replace(/\n\s+"force_backend":\s*true,\n/, '\n')
  fs.writeFileSync(dest, manifestText)
}

function syncManifestPlugin() {
  return {
    name: 'sync-manifest',
    buildStart() {
      // apps/studio is the cwd for Vite
      const src = path.resolve(process.cwd(), '../../projects/gridfinity/project.json')
      const dest = path.resolve(process.cwd(), 'src/config/fallback-manifest.json')
      try {
        if (fs.existsSync(src)) {
          writeFallbackManifest(src, dest)
          console.log('\x1b[32m%s\x1b[0m', '✅ Synced gridfinity manifest to fallback-manifest.json')
        }
      } catch (err) {
        console.warn('\x1b[33m%s\x1b[0m', '⚠️ Failed to sync fallback manifest: ' + err.message)
      }
    },
    // Watch for manifest changes during dev
    configureServer(server) {
      const src = path.resolve(process.cwd(), '../../projects/gridfinity/project.json')
      server.watcher.add(src)
      server.watcher.on('change', (file) => {
        if (file === src) {
          const dest = path.resolve(process.cwd(), 'src/config/fallback-manifest.json')
          writeFallbackManifest(src, dest)
          console.log('\x1b[32m%s\x1b[0m', '🔄 Synced gridfinity manifest (watched file changed)')
        }
      })
    }
  }
}

// robots.txt, sitemap.xml and llms.txt for app.yantra4d.com, built once per
// production build from the generated public-cartridge list (see
// src/lib/crawlFiles.js). The catalog is read at build time; a missing or empty
// one FAILS the build rather than shipping a sitemap with no cartridges. The
// Docker build copies docs/commons-catalog.json in for this (apps/studio/Dockerfile).
function crawlFilesPlugin() {
  return {
    name: 'crawl-files',
    apply: 'build',
    generateBundle() {
      const catalogPath = path.resolve(
        process.cwd(),
        process.env.STUDIO_COMMONS_CATALOG ?? '../../docs/commons-catalog.json',
      )
      let catalog
      try {
        catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'))
      } catch (err) {
        throw new Error(`crawl-files: cannot read the commons catalog at ${catalogPath}: ${err.message}`)
      }
      const slugs = catalogSlugs(catalog)
      const origin = process.env.STUDIO_SITE_ORIGIN || DEFAULT_STUDIO_ORIGIN
      this.emitFile({ type: 'asset', fileName: 'sitemap.xml', source: buildSitemap(origin, slugs) })
      this.emitFile({ type: 'asset', fileName: 'robots.txt', source: buildRobots(origin) })
      this.emitFile({ type: 'asset', fileName: 'llms.txt', source: buildLlms(origin, slugs) })
      console.log('\x1b[32m%s\x1b[0m', `✅ crawl files: sitemap.xml (${slugs.length} cartridges), robots.txt, llms.txt`)
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    syncManifestPlugin(),
    crawlFilesPlugin(),
    process.env.ANALYZE && visualizer({ open: true, gzipSize: true, filename: 'dist/stats.html' }),
  ].filter(Boolean),
  base: '/',
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
      },
      '/static': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
      }
    },
    watch: {
      usePolling: true,
      interval: 100,
      ignored: ['**/backend/**', '**/*.stl']
    }
  },
  worker: {
    format: 'es'
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/')) {
            return 'vendor-react'
          }
          // The meshopt decoder is imported dynamically with the prerendered
          // preview (useWorkerLoader); left out of vendor-three it gets its own
          // lazy chunk instead of riding in the eager one.
          if (id.includes('node_modules/three/') && !id.includes('meshopt_decoder')) {
            return 'vendor-three'
          }
          if (id.includes('node_modules/@react-three/')) {
            return 'vendor-r3f'
          }
          if (id.includes('node_modules/@radix-ui/')) {
            return 'vendor-ui'
          }
        }
      }
    },
    chunkSizeWarningLimit: 1000,
  },
})
