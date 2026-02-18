/**
 * useJanuaAuth — wraps @janua/react-sdk with a local dev bypass.
 *
 * When VITE_AUTH_ENABLED !== 'true' (the default for local dev),
 * returns a synthetic admin user without contacting Janua.
 *
 * In production (VITE_AUTH_ENABLED=true), delegates to the real
 * useAuth hook from @janua/react-sdk.
 */
import { useAuth } from '@janua/react-sdk'

const AUTH_ENABLED = import.meta.env.VITE_AUTH_ENABLED === 'true'

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
    // In production, use the real Janua SDK hook
    const janua = AUTH_ENABLED ? useAuth() : null  // eslint-disable-line react-hooks/rules-of-hooks

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
        user: janua.user ?? null,
        isAuthenticated: !!janua.user,
        isLoading: janua.isLoading ?? false,
        signIn: janua.signIn,
        signOut: janua.signOut,
    }
}
