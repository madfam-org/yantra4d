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
function JanuaBridge({ children }: AuthProviderProps) {
  const janua = useJanua()
  return (
    <AuthContext.Provider value={janua}>
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
