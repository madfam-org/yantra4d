import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { useEffect, useState } from 'react'

// Mock @janua/react-sdk to avoid duplicate-React issues with npm-linked package
vi.mock('@janua/react-sdk', () => ({
  JanuaProvider: ({ children }) => children,
  useJanua: () => ({}),
}))

// Ensure bypass mode by clearing the env var before importing
vi.stubEnv('VITE_JANUA_BASE_URL', '')

const { AuthProvider, useAuth } = await import('./AuthProvider')

function AuthConsumer() {
  const auth = useAuth()
  return (
    <div>
      <span data-testid="authenticated">{String(auth.isAuthenticated)}</span>
      <span data-testid="loading">{String(auth.isLoading)}</span>
      <span data-testid="user">{auth.user ? auth.user.email : 'null'}</span>
    </div>
  )
}

describe('AuthProvider (bypass mode)', () => {
  it('renders children', () => {
    render(
      <AuthProvider>
        <div data-testid="child">Hello</div>
      </AuthProvider>
    )
    expect(screen.getByTestId('child')).toHaveTextContent('Hello')
  })

  it('provides no-op auth context', () => {
    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    )
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false')
    expect(screen.getByTestId('loading')).toHaveTextContent('false')
    expect(screen.getByTestId('user')).toHaveTextContent('null')
  })

  it('getAccessToken returns null', async () => {
    function TokenChecker() {
      const { getAccessToken } = useAuth()
      const [result, setResult] = useState('pending')
      useEffect(() => {
        getAccessToken().then(t => setResult(t === null ? 'null' : 'not-null'))
      }, [getAccessToken])
      return <span data-testid="token">{result}</span>
    }
    render(
      <AuthProvider>
        <TokenChecker />
      </AuthProvider>
    )
    await vi.waitFor(() => expect(screen.getByTestId('token')).toHaveTextContent('null'))
  })

  it('useAuth returns BYPASS_VALUE when context is null', () => {
    function DirectConsumer() {
      const auth = useAuth()
      return <span data-testid="is-auth">{String(auth.isAuthenticated)}</span>
    }
    // Render outside AuthProvider, context is null → returns bypass
    render(<DirectConsumer />)
    expect(screen.getByTestId('is-auth')).toHaveTextContent('false')
  })

  it('isAuthEnabled is false in bypass mode', async () => {
    const { isAuthEnabled } = await import('./AuthProvider')
    expect(isAuthEnabled).toBe(false)
  })
})

describe('AuthProvider (Janua mode)', () => {
  it('renders JanuaAuthProvider when JANUA_BASE_URL is set', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_JANUA_BASE_URL', 'https://auth.example.com')

    // Re-mock @janua/react-sdk with useJanua returning mock auth state
    vi.doMock('@janua/react-sdk', () => ({
      JanuaProvider: ({ children }) => <div data-testid="janua-provider">{children}</div>,
      useJanua: () => ({
        user: { email: 'test@example.com' },
        isAuthenticated: true,
        isLoading: false,
        error: null,
        signIn: async () => {},
        signUp: async () => {},
        signOut: async () => {},
        signInWithOAuth: async () => {},
        handleOAuthCallback: async () => {},
        getAccessToken: async () => 'mock-token',
        getIdToken: async () => 'mock-id-token',
        clearError: () => {},
        refreshSession: async () => {},
      }),
    }))

    const { AuthProvider: JanuaAuthProvider, useAuth: useJanuaAuth } = await import('./AuthProvider')

    function JanuaConsumer() {
      const auth = useJanuaAuth()
      return (
        <div>
          <span data-testid="janua-authenticated">{String(auth.isAuthenticated)}</span>
          <span data-testid="janua-user">{auth.user?.email || 'null'}</span>
        </div>
      )
    }

    render(
      <JanuaAuthProvider>
        <JanuaConsumer />
      </JanuaAuthProvider>
    )

    expect(screen.getByTestId('janua-provider')).toBeInTheDocument()
    expect(screen.getByTestId('janua-authenticated')).toHaveTextContent('true')
    expect(screen.getByTestId('janua-user')).toHaveTextContent('test@example.com')

    // Restore env
    vi.stubEnv('VITE_JANUA_BASE_URL', '')
  })

  it('reports isAuthenticated from a stored session even when the SDK reports signed-out', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_JANUA_BASE_URL', 'https://auth.example.com')

    // The SDK derives isAuthenticated from `user`, loaded via Janua's
    // /api/v1/auth/me — which rejects a yantra4d-api-audience token — so after a
    // successful OIDC sign-in the SDK reports signed-out. A valid stored token
    // must still count as authenticated, or the private-project gate stays locked.
    vi.doMock('@janua/react-sdk', () => ({
      JanuaProvider: ({ children }) => <div>{children}</div>,
      useJanua: () => ({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        getAccessToken: async () => null,
      }),
    }))

    const b64url = (o) =>
      btoa(JSON.stringify(o)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
    const token = `${b64url({ alg: 'none' })}.${b64url({ exp: Math.floor(Date.now() / 1000) + 3600 })}.sig`
    localStorage.setItem('janua_access_token', token)

    const { AuthProvider: StoredAuthProvider, useAuth: useStoredAuth } = await import('./AuthProvider')
    function StoredConsumer() {
      const auth = useStoredAuth()
      return <span data-testid="stored-auth">{String(auth.isAuthenticated)}</span>
    }
    render(
      <StoredAuthProvider>
        <StoredConsumer />
      </StoredAuthProvider>
    )
    expect(screen.getByTestId('stored-auth')).toHaveTextContent('true')

    localStorage.removeItem('janua_access_token')
    vi.stubEnv('VITE_JANUA_BASE_URL', '')
  })
})
