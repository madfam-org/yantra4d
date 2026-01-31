import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import AuthGate from './AuthGate'

const mockAuth = { isAuthenticated: false }
const mockManifest = { manifest: {} }

vi.mock('../contexts/AuthProvider', () => ({
  useAuth: () => mockAuth,
  isAuthEnabled: true,
}))

vi.mock('../contexts/ManifestProvider', () => ({
  useManifest: () => mockManifest,
}))

describe('AuthGate', () => {
  it('shows children when action is public', () => {
    mockManifest.manifest = {}
    render(
      <AuthGate action="download_stl">
        <span data-testid="child">Download</span>
      </AuthGate>
    )
    expect(screen.getByTestId('child')).toBeInTheDocument()
  })

  it('shows children when action is public explicitly', () => {
    mockManifest.manifest = { access_control: { download_stl: 'public' } }
    render(
      <AuthGate action="download_stl">
        <span data-testid="child">Download</span>
      </AuthGate>
    )
    expect(screen.getByTestId('child')).toBeInTheDocument()
  })

  it('shows children when authenticated and action requires auth', () => {
    mockAuth.isAuthenticated = true
    mockManifest.manifest = { access_control: { download_stl: 'authenticated' } }
    render(
      <AuthGate action="download_stl">
        <span data-testid="child">Download</span>
      </AuthGate>
    )
    expect(screen.getByTestId('child')).toBeInTheDocument()
  })

  it('shows fallback when unauthenticated and action requires auth', () => {
    mockAuth.isAuthenticated = false
    mockManifest.manifest = { access_control: { download_stl: 'authenticated' } }
    render(
      <AuthGate action="download_stl" fallback={<span data-testid="fallback">Sign in</span>}>
        <span data-testid="child">Download</span>
      </AuthGate>
    )
    expect(screen.queryByTestId('child')).not.toBeInTheDocument()
    expect(screen.getByTestId('fallback')).toBeInTheDocument()
  })
})
