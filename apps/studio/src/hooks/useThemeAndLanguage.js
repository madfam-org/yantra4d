import { useEffect, useCallback } from 'react'
import { useTheme } from '../contexts/ThemeProvider'
import { useLanguage } from '../contexts/LanguageProvider'
import { useAuth } from '../contexts/AuthProvider'
import { setTokenGetter } from '../services/core/apiClient'

/**
 * Composes theme cycling, language toggling, document-title sync,
 * OAuth callback handling, and auth-token wiring into the API client.
 */
export function useThemeAndLanguage({ currentView, projectName }) {
  const { theme, setTheme } = useTheme()
  const { language, setLanguage, t } = useLanguage()
  const { handleOAuthCallback: handleOAuth, getAccessToken } = useAuth()

  // Wire auth token into shared API client
  useEffect(() => {
    setTokenGetter(getAccessToken)
  }, [getAccessToken])

  // Dynamic browser tab title
  useEffect(() => {
    document.title = currentView === 'projects'
      ? 'Yantra4D'
      : `${projectName} — Yantra4D`
  }, [currentView, projectName])

  // Handle OAuth callback
  useEffect(() => {
    const url = new URL(window.location.href)
    const code = url.searchParams.get('code')
    const state = url.searchParams.get('state')
    if (code && state) {
      handleOAuth(code, state).catch((err) => console.error('OAuth callback failed:', err))
      url.searchParams.delete('code')
      url.searchParams.delete('state')
      window.history.replaceState({}, '', url.pathname + url.hash)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const cycleTheme = useCallback(() => {
    const themes = ['light', 'dark', 'system']
    const currentIndex = themes.indexOf(theme)
    setTheme(themes[(currentIndex + 1) % themes.length])
  }, [theme, setTheme])

  const toggleLanguage = useCallback(() => {
    setLanguage(language === 'es' ? 'en' : 'es')
  }, [language, setLanguage])

  return {
    theme,
    cycleTheme,
    language,
    setLanguage,
    toggleLanguage,
    t,
  }
}
