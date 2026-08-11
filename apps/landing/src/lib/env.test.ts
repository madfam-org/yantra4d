import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

/**
 * env.ts resolves service URLs at module load, so each case needs a fresh
 * import with the environment and hostname already in place.
 *
 * This matters: a wrong resolution here is exactly the failure that ships a
 * dev URL to production users.
 */
async function loadEnv() {
    return import('./env')
}

function setHostname(hostname: string) {
    Object.defineProperty(window, 'location', {
        value: { ...window.location, hostname },
        writable: true,
        configurable: true,
    })
}

describe('env URL resolution', () => {
    beforeEach(() => {
        vi.resetModules()
    })
    afterEach(() => {
        vi.unstubAllEnvs()
        vi.resetModules()
    })

    it('points at production services when built for production on a real host', async () => {
        vi.stubEnv('DEV', false)
        setHostname('yantra4d.com')
        const { STUDIO_URL, API_URL } = await loadEnv()
        expect(STUDIO_URL).toBe('https://app.yantra4d.com')
        expect(API_URL).toBe('https://api.yantra4d.com')
    })

    it('points at local services in dev mode', async () => {
        vi.stubEnv('DEV', true)
        setHostname('yantra4d.com')
        const { STUDIO_URL, API_URL } = await loadEnv()
        expect(STUDIO_URL).toBe('http://localhost:5173')
        expect(API_URL).toBe('http://localhost:5000')
    })

    it('treats a localhost hostname as local even in a production build', async () => {
        vi.stubEnv('DEV', false)
        setHostname('localhost')
        const { STUDIO_URL, API_URL } = await loadEnv()
        expect(STUDIO_URL).toBe('http://localhost:5173')
        expect(API_URL).toBe('http://localhost:5000')
    })

    it('treats 127.0.0.1 as local as well', async () => {
        vi.stubEnv('DEV', false)
        setHostname('127.0.0.1')
        const { API_URL } = await loadEnv()
        expect(API_URL).toBe('http://localhost:5000')
    })

    it('lets an explicit PUBLIC_STUDIO_URL win over both defaults', async () => {
        vi.stubEnv('DEV', true)
        vi.stubEnv('PUBLIC_STUDIO_URL', 'https://staging.yantra4d.com')
        setHostname('localhost')
        const { STUDIO_URL, API_URL } = await loadEnv()
        expect(STUDIO_URL).toBe('https://staging.yantra4d.com')
        // API_URL has no override and must still follow the local check.
        expect(API_URL).toBe('http://localhost:5000')
    })
})
