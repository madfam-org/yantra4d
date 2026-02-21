import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import React from 'react'

// --- Mocks ---
const mockSetTheme = vi.fn()
const mockSetLanguage = vi.fn()
const mockHandleOAuth = vi.fn().mockResolvedValue()
const mockGetAccessToken = vi.fn()
const mockSetTokenGetter = vi.fn()

vi.mock('../contexts/ThemeProvider', () => ({
  useTheme: () => ({
    theme: 'light',
    setTheme: mockSetTheme,
  }),
}))

vi.mock('../contexts/LanguageProvider', () => ({
  useLanguage: () => ({
    language: 'en',
    setLanguage: mockSetLanguage,
    t: (key) => key,
  }),
}))

vi.mock('../contexts/AuthProvider', () => ({
  useAuth: () => ({
    handleOAuthCallback: mockHandleOAuth,
    getAccessToken: mockGetAccessToken,
  }),
}))

vi.mock('../services/core/apiClient', () => ({
  setTokenGetter: (...args) => mockSetTokenGetter(...args),
}))

import { useThemeAndLanguage } from './useThemeAndLanguage'

describe('useThemeAndLanguage', () => {
  const originalTitle = document.title

  beforeEach(() => {
    vi.clearAllMocks()
    document.title = originalTitle
    // Clean up URL params
    window.history.replaceState({}, '', window.location.pathname + window.location.hash)
  })

  afterEach(() => {
    document.title = originalTitle
  })

  function renderTL(overrides = {}) {
    const defaults = { currentView: 'studio', projectName: 'TestProject' }
    return renderHook(() => useThemeAndLanguage({ ...defaults, ...overrides }))
  }

  // ---------- Return values ----------
  it('returns theme, cycleTheme, language, setLanguage, toggleLanguage, t', () => {
    const { result } = renderTL()
    expect(result.current).toHaveProperty('theme', 'light')
    expect(result.current).toHaveProperty('language')
    expect(typeof result.current.cycleTheme).toBe('function')
    expect(typeof result.current.toggleLanguage).toBe('function')
    expect(typeof result.current.setLanguage).toBe('function')
    expect(typeof result.current.t).toBe('function')
  })

  // ---------- Token wiring ----------
  it('wires auth token getter into API client on mount', () => {
    renderTL()
    expect(mockSetTokenGetter).toHaveBeenCalledWith(mockGetAccessToken)
  })

  // ---------- Document title ----------
  it('sets document title with project name for studio view', () => {
    renderTL({ currentView: 'studio', projectName: 'MyProject' })
    expect(document.title).toBe('MyProject — Yantra4D')
  })

  it('sets document title to Yantra4D for projects view', () => {
    renderTL({ currentView: 'projects', projectName: 'MyProject' })
    expect(document.title).toBe('Yantra4D')
  })

  // ---------- cycleTheme ----------
  it('cycles theme from light to dark', () => {
    const { result } = renderTL()
    act(() => { result.current.cycleTheme() })
    expect(mockSetTheme).toHaveBeenCalledWith('dark')
  })

  // ---------- toggleLanguage ----------
  it('toggles language from en to es', () => {
    const { result } = renderTL()
    act(() => { result.current.toggleLanguage() })
    expect(mockSetLanguage).toHaveBeenCalledWith('es')
  })

  // ---------- t function ----------
  it('t function returns translation key', () => {
    const { result } = renderTL()
    expect(result.current.t('hello')).toBe('hello')
  })

  // ---------- OAuth callback ----------
  it('handles OAuth callback when code and state are in URL', () => {
    // Set URL with OAuth params
    const url = new URL(window.location.href)
    url.searchParams.set('code', 'abc123')
    url.searchParams.set('state', 'xyz789')
    window.history.replaceState({}, '', url.toString())

    renderTL()

    expect(mockHandleOAuth).toHaveBeenCalledWith('abc123', 'xyz789')
  })

  it('does not call handleOAuth when no code/state in URL', () => {
    renderTL()
    expect(mockHandleOAuth).not.toHaveBeenCalled()
  })
})
