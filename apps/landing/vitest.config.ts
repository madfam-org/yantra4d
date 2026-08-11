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
      exclude: ['src/test/**'],
      // TARGET is 60% across the board. These are an enforced
      // NON-REGRESSION FLOOR at the coverage actually measured on 2026-08-11,
      // not an endorsement of that level.
      //
      // The 60% threshold was never enforced: the landing job runs
      // `npm audit` before `test:coverage`, and audit had been failing, so the
      // coverage step was skipped on every run. Unblocking audit surfaced the
      // real number for the first time. Raise these as tests land; never lower.
      thresholds: {
        statements: 50,
        branches: 48,
        functions: 66,
        lines: 53,
      },
    },
  },
})
