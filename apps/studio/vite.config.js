/* global process */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'
import fs from 'fs'
import path from 'path'

// Custom plugin to keep fallback manifest continuously in sync with the flagship project (Gridfinity)
function syncManifestPlugin() {
  return {
    name: 'sync-manifest',
    buildStart() {
      // apps/studio is the cwd for Vite
      const src = path.resolve(process.cwd(), '../../projects/gridfinity/project.json')
      const dest = path.resolve(process.cwd(), 'src/config/fallback-manifest.json')
      try {
        if (fs.existsSync(src)) {
          fs.copyFileSync(src, dest)
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
          fs.copyFileSync(src, dest)
          console.log('\x1b[32m%s\x1b[0m', '🔄 Synced gridfinity manifest (watched file changed)')
        }
      })
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    syncManifestPlugin(),
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
          if (id.includes('node_modules/three/')) {
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
