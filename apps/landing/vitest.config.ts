import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      // src/components/vendor/** is code synced in from the shared MADFAM
      // ecosystem-banner package, not authored here. Tests written against it
      // in this repo would duplicate the upstream suite and break on every
      // sync, so it is measured upstream rather than counted in this denominator.
      exclude: ['src/test/**', 'src/components/vendor/**'],
      thresholds: {
        statements: 60,
        branches: 60,
        functions: 60,
        lines: 60,
      },
    },
  },
})
