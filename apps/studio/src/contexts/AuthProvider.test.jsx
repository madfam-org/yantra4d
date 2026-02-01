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
})
