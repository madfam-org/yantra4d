import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { createRequire } from 'module'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// This app renders shared UI components that live in apps/studio. Rolldown
// (Vite 8) resolves a bare import relative to the importing file, so those
// components look for their dependencies under apps/studio/node_modules —
// which CI never installs, because the admin job installs only apps/admin.
// Vite 5 quietly fell back to the project root; Rolldown does not, and the
// build failed on "react", then "class-variance-authority", and so on.
//
// Deduping every dependency this app declares pins them all to this app's own
// copy regardless of which file imports them. Derived from package.json so a
// new dependency is covered without anyone remembering to add it here.
const pkg = createRequire(import.meta.url)('./package.json')
const OWN_DEPENDENCIES = Object.keys(pkg.dependencies ?? {})

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, process.cwd(), '')

    return {
        plugins: [react()],
        base: '/',
        resolve: {
            alias: {
                // Share shadcn UI components from studio
                '@/components': path.resolve(__dirname, '../studio/src/components'),
                '@/lib': path.resolve(__dirname, '../studio/src/lib'),
                '@/hooks': path.resolve(__dirname, '../studio/src/hooks'),
                // Admin-local src shorthand
                '@admin': path.resolve(__dirname, 'src'),
            },
            dedupe: OWN_DEPENDENCIES,
        },
        server: {
            port: 5174,
            proxy: {
                '/api': {
                    target: env.VITE_API_URL || 'http://localhost:5000',
                    changeOrigin: true,
                },
            },
        },
        build: {
            outDir: 'dist',
        },
    }
})
