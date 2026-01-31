/* global process */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    process.env.ANALYZE && visualizer({ open: true, gzipSize: true, filename: 'dist/stats.html' }),
  ].filter(Boolean),
  base: process.env.GITHUB_ACTIONS ? '/qubic/' : '/',
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    watch: {
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
