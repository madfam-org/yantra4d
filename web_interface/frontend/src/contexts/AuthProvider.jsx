/**
 * Auth provider that wraps @janua/react-sdk's JanuaProvider.
 * Falls back to a no-op bypass when VITE_JANUA_BASE_URL is not configured
 * (e.g., static deployment or local dev without Janua).
 *
 * Uses a bridge pattern to avoid conditional hook calls (Rules of Hooks).
 */
import { createContext, useContext, useMemo } from 'react'

const JANUA_BASE_URL = import.meta.env.VITE_JANUA_BASE_URL
const JANUA_CLIENT_ID = import.meta.env.VITE_JANUA_CLIENT_ID || 'qubic'
const JANUA_REDIRECT_URI = import.meta.env.VITE_JANUA_REDIRECT_URI || (typeof window !== 'undefined' ? window.location.origin : '')

const AuthContext = createContext(null)

/** No-op auth context for when Janua is not configured */
const BYPASS_VALUE = {
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

function AuthBypassProvider({ children }) {
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
function JanuaBridge({ children }) {
  // eslint-disable-next-line no-undef
  const { useJanua } = require('@janua/react-sdk')
  const janua = useJanua()
  return (
    <AuthContext.Provider value={janua}>
      {children}
    </AuthContext.Provider>
  )
}

function JanuaAuthProvider({ children }) {
  const config = useMemo(() => ({
    baseURL: JANUA_BASE_URL,
    clientId: JANUA_CLIENT_ID,
    redirectUri: JANUA_REDIRECT_URI,
  }), [])

  // eslint-disable-next-line no-undef
  const { JanuaProvider } = require('@janua/react-sdk')

  return (
    <JanuaProvider config={config}>
      <JanuaBridge>{children}</JanuaBridge>
    </JanuaProvider>
  )
}

export function AuthProvider({ children }) {
  if (!JANUA_BASE_URL) {
    return <AuthBypassProvider>{children}</AuthBypassProvider>
  }
  return <JanuaAuthProvider>{children}</JanuaAuthProvider>
}

/**
 * Unified auth hook. Always a single useContext call — no conditional hooks.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext)
  return context || BYPASS_VALUE
}

/** Whether auth is configured at all */
export const isAuthEnabled = !!JANUA_BASE_URL
