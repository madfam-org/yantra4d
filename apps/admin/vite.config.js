import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

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
        },
        server: {
            port: 5174,
            proxy: {
                '/api': {
                    target: env.VITE_API_URL || 'http://localhost:8000',
                    changeOrigin: true,
                },
            },
        },
        build: {
            outDir: 'dist',
        },
    }
})
