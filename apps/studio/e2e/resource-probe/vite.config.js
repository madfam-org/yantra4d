import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// A separate local entry point: no production API, manifest writes or debug UI.
export default defineConfig({
  plugins: [react()],
  worker: { format: 'es' },
  optimizeDeps: {
    entries: ['e2e/resource-probe/index.html'],
    include: ['three/examples/jsm/loaders/STLLoader'],
  },
})
