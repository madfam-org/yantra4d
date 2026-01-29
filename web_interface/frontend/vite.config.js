/* global process */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: process.env.GITHUB_ACTIONS ? '/tablaco/' : '/',
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
  }
})
