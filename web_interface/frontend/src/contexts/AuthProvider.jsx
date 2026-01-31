/**
 * Auth provider that wraps @janua/react-sdk's JanuaProvider.
 * Falls back to a no-op bypass when VITE_JANUA_BASE_URL is not configured
 * (e.g., GitHub Pages deployment or local dev without Janua).
 */
import { createContext, useContext, useMemo } from 'react'

const JANUA_BASE_URL = import.meta.env.VITE_JANUA_BASE_URL
const JANUA_CLIENT_ID = import.meta.env.VITE_JANUA_CLIENT_ID || 'tablaco'
const JANUA_REDIRECT_URI = import.meta.env.VITE_JANUA_REDIRECT_URI || (typeof window !== 'undefined' ? window.location.origin : '')

const AuthBypassContext = createContext(null)

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
    <AuthBypassContext.Provider value={BYPASS_VALUE}>
      {children}
    </AuthBypassContext.Provider>
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
      {children}
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
 * Unified auth hook. Uses Janua's useJanua() when configured,
 * or the bypass context when not.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const bypass = useContext(AuthBypassContext)
  if (bypass) return bypass

  try {
    // eslint-disable-next-line no-undef
    const { useJanua } = require('@janua/react-sdk')
    // eslint-disable-next-line react-hooks/rules-of-hooks
    return useJanua()
  } catch {
    return BYPASS_VALUE
  }
}

/** Whether auth is configured at all */
export const isAuthEnabled = !!JANUA_BASE_URL
