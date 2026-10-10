import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./lib/analytics', () => ({
    initPostHog: vi.fn(),
}))

vi.mock('./App.jsx', () => ({
    default: () => <div data-testid="app">App</div>,
}))

vi.mock('@janua/react-sdk', () => ({
    JanuaProvider: ({ config, children }) => (
        <div data-testid="janua-provider" data-client-id={config.clientId}>
            {children}
        </div>
    ),
}))

async function loadMain() {
    vi.resetModules()
    await import('./main.jsx')
    // bootstrap() is async and floating; let its microtasks and React's render
    // settle before asserting on the DOM.
    await new Promise((resolve) => setTimeout(resolve, 0))
}

describe('admin bootstrap', () => {
    let errorSpy

    beforeEach(() => {
        document.body.innerHTML = '<div id="root"></div>'
        errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    })

    afterEach(() => {
        vi.unstubAllEnvs()
        errorSpy.mockRestore()
        document.body.innerHTML = ''
    })

    it('renders the app without Janua when authentication is disabled', async () => {
        vi.stubEnv('VITE_AUTH_ENABLED', 'false')
        vi.stubEnv('VITE_JANUA_CLIENT_ID', '')

        await loadMain()

        expect(document.querySelector('[data-testid="app"]')).not.toBeNull()
        expect(document.querySelector('[data-testid="janua-provider"]')).toBeNull()
    })

    it('passes the build-time client id through to JanuaProvider', async () => {
        vi.stubEnv('VITE_AUTH_ENABLED', 'true')
        vi.stubEnv('VITE_JANUA_CLIENT_ID', 'test-client')

        await loadMain()

        const provider = document.querySelector('[data-testid="janua-provider"]')
        expect(provider).not.toBeNull()
        expect(provider.getAttribute('data-client-id')).toBe('test-client')
    })

    it('fails loudly instead of inventing a client id when the variable is empty', async () => {
        vi.stubEnv('VITE_AUTH_ENABLED', 'true')
        vi.stubEnv('VITE_JANUA_CLIENT_ID', '')

        await loadMain()

        expect(document.querySelector('[data-testid="janua-provider"]')).toBeNull()
        expect(document.querySelector('[data-testid="app"]')).toBeNull()
        expect(document.querySelector('[role="alert"]')).not.toBeNull()

        const logged = errorSpy.mock.calls.map((call) => call.join(' ')).join('\n')
        expect(logged).toContain('VITE_JANUA_CLIENT_ID')
        expect(logged).toContain('JANUA_ADMIN_CLIENT_ID')
    })

    it('does not throw at import time when the variable is missing', async () => {
        vi.stubEnv('VITE_AUTH_ENABLED', 'true')
        vi.stubEnv('VITE_JANUA_CLIENT_ID', '')

        await expect(loadMain()).resolves.toBeUndefined()
    })
})
