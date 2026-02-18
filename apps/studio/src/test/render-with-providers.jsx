import React from 'react'
import { render } from '@testing-library/react'
import { ThemeProvider } from '../contexts/ThemeProvider'
import { LanguageProvider } from '../contexts/LanguageProvider'
import { AuthProvider } from '../contexts/AuthProvider'
import { ManifestProvider } from '../contexts/ManifestProvider'
import { ProjectProvider } from '../contexts/ProjectProvider'
import { TierContext } from '../contexts/TierProvider'

const TIER_HIERARCHY = { guest: 0, basic: 1, pro: 2, madfam: 3 }

/**
 * Render a component wrapped in all application providers.
 *
 * @param {React.ReactElement} ui - The component to render
 * @param {object} [options] - Options
 * @param {string} [options.language='en'] - Default language
 * @param {string} [options.theme='light'] - Default theme
 * @param {string} [options.tier='guest'] - User tier
 * @param {object} [options.renderOptions] - Additional options passed to RTL render
 * @returns RTL render result
 */
export function renderWithProviders(ui, { language = 'en', theme = 'light', tier = 'guest', ...renderOptions } = {}) {
  const tierValue = {
    tier,
    tierConfig: null,
    limits: null,
    allTiers: null,
    loading: false,
    canAccess: (required) => (TIER_HIERARCHY[tier] ?? 0) >= (TIER_HIERARCHY[required] ?? 0),
  }

  return render(
    <ThemeProvider defaultTheme={theme} storageKey="test-theme">
      <LanguageProvider defaultLanguage={language} storageKey="test-lang">
        <AuthProvider>
          <ManifestProvider>
            <TierContext.Provider value={tierValue}>
              <ProjectProvider>
                {ui}
              </ProjectProvider>
            </TierContext.Provider>
          </ManifestProvider>
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>,
    renderOptions
  )
}

