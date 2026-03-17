/**
 * useJanuaAuth — wraps @janua/react-sdk with a local dev bypass.
 *
 * When VITE_AUTH_ENABLED !== 'true' (the default for local dev),
 * returns a synthetic admin user without contacting Janua.
 *
 * In production (VITE_AUTH_ENABLED=true), delegates to the real
 * useAuth hook from @janua/react-sdk which consumes JanuaProvider context.
 * Authentication uses the OIDC/PKCE redirect flow — no direct fetch to
 * auth.madfam.io from the browser (avoids CORS issues).
 */
import { useAuth } from '@janua/react-sdk'

export const AUTH_ENABLED = import.meta.env.VITE_AUTH_ENABLED === 'true'

const DEV_USER = {
    id: 'dev-local',
    email: 'dev@local',
    roles: ['admin'],
    name: 'Local Dev Admin',
}

/**
 * @returns {{ user, isAuthenticated, isLoading, signIn, signOut, signInWithOAuth, handleOAuthCallback, error, clearError }}
 */
export function useJanuaAuth() {
    // Always call useAuth — when AUTH_ENABLED is false, JanuaProvider is not
    // in the tree so we gate the call to avoid the "must be inside JanuaProvider" error.
    // This is intentionally conditional on a build-time constant (not runtime state),
    // so the hook call order is deterministic per build.
    if (!AUTH_ENABLED) {
        return {
            user: DEV_USER,
            isAuthenticated: true,
            isLoading: false,
            error: null,
            signIn: async () => { },
            signOut: async () => { },
            signInWithOAuth: async () => { },
            handleOAuthCallback: async () => { },
            clearError: () => { },
        }
    }

    const auth = useAuth() // eslint-disable-line react-hooks/rules-of-hooks

    return {
        user: auth.user ?? null,
        isAuthenticated: auth.isAuthenticated,
        isLoading: auth.isLoading,
        error: auth.error,
        signIn: auth.signIn,
        signOut: auth.signOut,
        signInWithOAuth: auth.signInWithOAuth,
        handleOAuthCallback: auth.handleOAuthCallback,
        clearError: auth.clearError,
    }
}
