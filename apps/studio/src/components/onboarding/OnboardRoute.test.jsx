import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { axe } from '../../test/axe-setup'
import { toHaveNoViolations } from 'jest-axe'
import { LanguageProvider } from '../../contexts/system/LanguageProvider'

expect.extend(toHaveNoViolations)

// `isAuthEnabled` is a module constant (set from VITE_JANUA_BASE_URL at build
// time); a getter lets each test choose it.
const auth = vi.hoisted(() => ({ enabled: true, isAuthenticated: false, admin: false }))
vi.mock('../../contexts/auth/AuthProvider', () => ({
  get isAuthEnabled() { return auth.enabled },
  useAuth: () => ({ isAuthenticated: auth.isAuthenticated }),
}))
vi.mock('../../lib/januaSso', () => ({
  hasStoredPlatformAdminClaim: () => auth.admin,
}))
vi.mock('../auth/AuthButton', () => ({
  default: () => <button type="button">Sign in</button>,
}))
vi.mock('./OnboardingWizard', () => ({
  default: () => <div data-testid="onboarding-wizard" />,
}))

import OnboardRoute, { canUploadCartridges } from './OnboardRoute'
import { COMMONS_CONTRIBUTING_URL } from './ContributeByPullRequest'

function renderRoute() {
  return render(
    <MemoryRouter initialEntries={['/onboard']}>
      <LanguageProvider defaultLanguage="en" storageKey="test-lang-onboard">
        <Routes>
          <Route path="/onboard" element={<OnboardRoute />} />
          <Route path="/projects" element={<div data-testid="projects-view" />} />
        </Routes>
      </LanguageProvider>
    </MemoryRouter>,
  )
}

describe('OnboardRoute', () => {
  beforeEach(() => {
    auth.enabled = true
    auth.isAuthenticated = false
    auth.admin = false
  })

  it('offers the upload wizard to a platform administrator', () => {
    auth.isAuthenticated = true
    auth.admin = true
    renderRoute()
    expect(screen.getByTestId('onboarding-wizard')).toBeInTheDocument()
    expect(screen.queryByTestId('onboard-contribute')).not.toBeInTheDocument()
  })

  it('offers the wizard with auth off, where the API lets every caller upload (local dev, e2e)', () => {
    auth.enabled = false
    renderRoute()
    expect(screen.getByTestId('onboarding-wizard')).toBeInTheDocument()
  })

  it('tells a signed-in non-admin that designs join by pull request, and links the real guide', () => {
    auth.isAuthenticated = true
    renderRoute()
    expect(screen.queryByTestId('onboarding-wizard')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'New designs join the Hyperobjects Commons by pull request' })).toBeInTheDocument()
    expect(screen.getByText(/limited to platform administrators/)).toBeInTheDocument()

    const guide = screen.getByRole('link', { name: /Read the contribution guide/ })
    expect(guide).toHaveAttribute('href', 'https://github.com/madfam-org/solid-hyperobjects/blob/main/CONTRIBUTING.md')
    expect(guide).toHaveAttribute('href', COMMONS_CONTRIBUTING_URL)
    expect(guide).toHaveAttribute('target', '_blank')
    expect(guide).toHaveAttribute('rel', expect.stringContaining('noopener'))
    expect(guide).toHaveAccessibleName(/opens in a new tab/)
    // Already signed in: no sign-in prompt.
    expect(screen.queryByText('Platform administrators: sign in to upload.')).not.toBeInTheDocument()
  })

  it('a signed-in session without the admin claim is not an admin', () => {
    auth.isAuthenticated = false
    auth.admin = true // a stale claim with no live session does not count
    expect(canUploadCartridges(false)).toBe(false)
    expect(canUploadCartridges(true)).toBe(true)
  })

  it('asks a signed-out visitor who administers the platform to sign in', () => {
    renderRoute()
    expect(screen.getByTestId('onboard-contribute')).toBeInTheDocument()
    expect(screen.getByText('Platform administrators: sign in to upload.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('Browse Projects goes to the catalog', () => {
    renderRoute()
    fireEvent.click(screen.getByRole('button', { name: 'Browse Projects' }))
    expect(screen.getByTestId('projects-view')).toBeInTheDocument()
  })

  it('has no axe violations', async () => {
    const { container } = renderRoute()
    expect(await axe(container)).toHaveNoViolations()
  })
})
