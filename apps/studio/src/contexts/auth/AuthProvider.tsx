/**
 * Auth provider that wraps @janua/react-sdk's JanuaProvider.
 * Falls back to a no-op bypass when VITE_JANUA_BASE_URL is not configured
 * (e.g., static deployment or local dev without Janua).
 *
 * Uses a bridge pattern to avoid conditional hook calls (Rules of Hooks).
 */
import { createContext, useContext, useMemo } from 'react'
import { JanuaProvider, useJanua } from '@janua/react-sdk'
import type { JanuaUser, JanuaErrorState, OAuthProviderName } from '@janua/react-sdk'
import { beginJanuaSignIn, completeJanuaSignIn, consumeReturnPath, hasStoredJanuaSession } from '../../lib/januaSso'

const JANUA_BASE_URL = import.meta.env.VITE_JANUA_BASE_URL as string | undefined
const JANUA_CLIENT_ID = (import.meta.env.VITE_JANUA_CLIENT_ID as string | undefined) || 'yantra4d'
const JANUA_REDIRECT_URI = (import.meta.env.VITE_JANUA_REDIRECT_URI as string | undefined) || (typeof window !== 'undefined' ? window.location.origin : '')

export interface AuthContextValue {
  user: JanuaUser | null
  isAuthenticated: boolean
  isLoading: boolean
  error: JanuaErrorState | null
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, options?: { firstName?: string; lastName?: string; username?: string }) => Promise<void>
  signOut: () => Promise<void>
  signInWithOAuth: (provider: OAuthProviderName) => Promise<void>
  /**
   * "Sign in with Janua": the OIDC authorization-code + PKCE flow against
   * Janua's hosted login. This is the sign-in the Studio uses. The SDK's
   * `signInWithOAuth(provider)` is the social-login proxy, which Janua does
   * not serve for a browser navigation (405) and has no providers configured
   * for — see `lib/januaSso.ts`. `returnTo` is the same-origin path to come
   * back to once the callback lands; it defaults to the current page.
   */
  signInWithJanua: (returnTo?: string) => Promise<void>
  handleOAuthCallback: (code: string, state: string) => Promise<void>
  getAccessToken: () => Promise<string | null>
  getIdToken: () => Promise<string | null>
  clearError: () => void
  refreshSession: () => Promise<void>
}

interface AuthProviderProps {
  children: React.ReactNode
}

const AuthContext = createContext<AuthContextValue | null>(null)

const BYPASS_VALUE: AuthContextValue = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  signIn: async () => {},
  signUp: async () => {},
  signOut: async () => {},
  signInWithOAuth: async () => {},
  signInWithJanua: async () => {},
  handleOAuthCallback: async () => {},
  getAccessToken: async () => null,
  getIdToken: async () => null,
  clearError: () => {},
  refreshSession: async () => {},
}

function AuthBypassProvider({ children }: AuthProviderProps) {
  return (
    <AuthContext.Provider value={BYPASS_VALUE}>
      {children}
    </AuthContext.Provider>
  )
}

/**
 * Bridge component: always renders inside JanuaProvider,
 * always calls useJanua(), and writes the result to AuthContext.
 */
const SSO_CONFIG = {
  baseURL: JANUA_BASE_URL ?? '',
  clientId: JANUA_CLIENT_ID,
  redirectUri: JANUA_REDIRECT_URI,
}

function JanuaBridge({ children }: AuthProviderProps) {
  const janua = useJanua()
  const value = useMemo<AuthContextValue>(() => ({
    ...janua,
    // The SDK derives `isAuthenticated` from `!!user`, and it loads `user` from
    // Janua's `GET /api/v1/auth/me` — which 401s on our `yantra4d-api`-audience
    // token. So a successful OIDC sign-in leaves the SDK `isAuthenticated:
    // false`, the private-project gate locked and the manifest re-fetch (keyed
    // on `signedIn`) never fires. A stored, unexpired token IS a session for
    // the Studio's own backend, so it counts as signed in.
    isAuthenticated: janua.isAuthenticated || hasStoredJanuaSession(),
    signInWithJanua: async (returnTo?: string) => {
      await beginJanuaSignIn(SSO_CONFIG, { returnTo })
    },
    // Replaces the SDK's callback, which POSTs JSON to a form-encoded token
    // endpoint. The tokens land under the SDK's own storage keys, so a full
    // navigation re-mounts JanuaProvider with the session — and brings the
    // user back to the page that asked for sign-in (the locked project).
    handleOAuthCallback: async (code: string, state: string) => {
      await completeJanuaSignIn(SSO_CONFIG, code, state)
      window.location.replace(consumeReturnPath() ?? '/')
    },
  }), [janua])
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

function JanuaAuthProvider({ children }: AuthProviderProps) {
  const config = useMemo(() => ({
    baseURL: JANUA_BASE_URL!,
    clientId: JANUA_CLIENT_ID,
    redirectUri: JANUA_REDIRECT_URI,
  }), [])

  return (
    <JanuaProvider config={config}>
      <JanuaBridge>{children}</JanuaBridge>
    </JanuaProvider>
  )
}

export function AuthProvider({ children }: AuthProviderProps) {
  if (!JANUA_BASE_URL) {
    return <AuthBypassProvider>{children}</AuthBypassProvider>
  }
  return <JanuaAuthProvider>{children}</JanuaAuthProvider>
}

/**
 * Unified auth hook. Always a single useContext call — no conditional hooks.
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  return context || BYPASS_VALUE
}

/** Whether auth is configured at all */
export const isAuthEnabled = !!JANUA_BASE_URL
