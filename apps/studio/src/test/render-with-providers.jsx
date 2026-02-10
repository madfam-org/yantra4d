import React from 'react'
import { render } from '@testing-library/react'
import { ThemeProvider } from '../contexts/ThemeProvider'
import { LanguageProvider } from '../contexts/LanguageProvider'
import { AuthProvider } from '../contexts/AuthProvider'
import { ManifestProvider } from '../contexts/ManifestProvider'
import { ProjectProvider } from '../contexts/ProjectProvider'

/**
 * Render a component wrapped in all application providers.
 *
 * @param {React.ReactElement} ui - The component to render
 * @param {object} [options] - Options
 * @param {string} [options.language='en'] - Default language
 * @param {string} [options.theme='light'] - Default theme
 * @param {object} [options.renderOptions] - Additional options passed to RTL render
 * @returns RTL render result
 */
export function renderWithProviders(ui, { language = 'en', theme = 'light', ...renderOptions } = {}) {
  return render(
    <ThemeProvider defaultTheme={theme} storageKey="test-theme">
      <LanguageProvider defaultLanguage={language} storageKey="test-lang">
        <AuthProvider>
          <ManifestProvider>
            <ProjectProvider>
              {ui}
            </ProjectProvider>
          </ManifestProvider>
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>,
    renderOptions
  )
}

