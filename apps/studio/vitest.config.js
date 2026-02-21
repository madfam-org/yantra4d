import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve, dirname } from 'path'
import { createRequire } from 'module'
import { fileURLToPath } from 'url'

// Use real @janua/react-sdk if installed, otherwise fall back to test stub
let januaAlias
try {
  const require = createRequire(import.meta.url)
  require.resolve('@janua/react-sdk')
} catch {
  const __dirname = dirname(fileURLToPath(import.meta.url))
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
        'src/locales/',
        'src/config/fallback-manifest.json',
      ],
      thresholds: {
        statements: 73,
        branches: 62,
        functions: 67,
        lines: 75,
      },
    },
  },
})
