import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { createRequire } from 'module'

// Use real @janua/react-sdk if installed, otherwise fall back to test stub
let januaAlias
try {
  const require = createRequire(import.meta.url)
  require.resolve('@janua/react-sdk')
} catch {
  januaAlias = resolve(__dirname, 'src/test/__mocks__/@janua/react-sdk.js')
}

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': '/src',
      ...(januaAlias ? { '@janua/react-sdk': januaAlias } : {}),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    include: ['src/**/*.test.{js,jsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      exclude: [
        'node_modules/',
        'src/test/',
        'src/components/ui/',
        '**/*.test.{js,jsx}',
      ],
      thresholds: {
        statements: 65,
        branches: 55,
        functions: 60,
        lines: 65,
      },
    },
  },
})
