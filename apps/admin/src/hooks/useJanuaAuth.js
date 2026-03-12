/**
 * useJanuaAuth — wraps @janua/react-sdk with a local dev bypass.
 *
 * When VITE_AUTH_ENABLED !== 'true' (the default for local dev),
 * returns a synthetic admin user without contacting Janua.
 *
 * In production (VITE_AUTH_ENABLED=true), delegates to the real
 * useAuth and useUser hooks from @janua/react-sdk.
 */
// Dynamic import at module level — set by init()
let _useAuth = null

const AUTH_ENABLED = import.meta.env.VITE_AUTH_ENABLED === 'true'

// Eagerly resolve the real hook if auth is enabled
if (AUTH_ENABLED) {
    import('@janua/react-sdk').then(mod => { _useAuth = mod.useAuth })
}

const DEV_USER = {
    id: 'dev-local',
    email: 'dev@local',
    roles: ['admin'],
    name: 'Local Dev Admin',
}

/**
 * @returns {{ user, isAuthenticated, isLoading, signIn, signOut }}
 */
export function useJanuaAuth() {
    // In production, use the real Janua SDK hooks
    const janua = AUTH_ENABLED && _useAuth ? _useAuth() : null  // eslint-disable-line react-hooks/rules-of-hooks

    if (!AUTH_ENABLED) {
        return {
            user: DEV_USER,
            isAuthenticated: true,
            isLoading: false,
            signIn: async () => { },
            signOut: async () => { },
        }
    }

    return {
        user: janua?.user ?? null,
        isAuthenticated: !!janua?.user,
        isLoading: janua?.isLoading ?? false,
        signIn: janua?.signIn,
        signOut: janua?.signOut,
    }
}
