import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { LanguageProvider, useLanguage } from './LanguageProvider'

function TestConsumer() {
  const { language, setLanguage, t } = useLanguage()
  return (
    <div>
      <span data-testid="lang">{language}</span>
      <span data-testid="text">{t('btn.gen')}</span>
      <span data-testid="missing">{t('nonexistent.key')}</span>
      <button onClick={() => setLanguage('en')}>EN</button>
      <button onClick={() => setLanguage('es')}>ES</button>
    </div>
  )
}

function TestThemeKeys() {
  const { t } = useLanguage()
  return (
    <div>
      <span data-testid="theme-light">{t('theme.light')}</span>
      <span data-testid="theme-dark">{t('theme.dark')}</span>
      <span data-testid="theme-system">{t('theme.system')}</span>
    </div>
  )
}

describe('LanguageProvider', () => {
  beforeEach(() => localStorage.clear())

  it('defaults to Spanish and translates correctly', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>
    )
    expect(screen.getByTestId('lang').textContent).toBe('es')
    expect(screen.getByTestId('text').textContent).toBe('Generar')
  })

  it('returns English text when language is en', () => {
    render(
      <LanguageProvider defaultLanguage="en">
        <TestConsumer />
      </LanguageProvider>
    )
    expect(screen.getByTestId('text').textContent).toBe('Generate')
  })

  it('returns key when key not found', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>
    )
    expect(screen.getByTestId('missing').textContent).toBe('nonexistent.key')
  })

  it('persists language to localStorage', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>
    )
    act(() => screen.getByText('EN').click())
    expect(localStorage.getItem('tablaco-lang')).toBe('en')
    expect(screen.getByTestId('text').textContent).toBe('Generate')
  })

  it('reads default language from localStorage', () => {
    localStorage.setItem('tablaco-lang', 'en')
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>
    )
    expect(screen.getByTestId('lang').textContent).toBe('en')
  })

  it('has theme translation keys in both languages', () => {
    // English
    const { unmount } = render(
      <LanguageProvider defaultLanguage="en">
        <TestThemeKeys />
      </LanguageProvider>
    )
    expect(screen.getByTestId('theme-light').textContent).toBe('Theme: Light')
    expect(screen.getByTestId('theme-dark').textContent).toBe('Theme: Dark')
    expect(screen.getByTestId('theme-system').textContent).toBe('Theme: System')
    unmount()

    // Spanish
    render(
      <LanguageProvider defaultLanguage="es">
        <TestThemeKeys />
      </LanguageProvider>
    )
    expect(screen.getByTestId('theme-light').textContent).toBe('Tema: Claro')
    expect(screen.getByTestId('theme-dark').textContent).toBe('Tema: Oscuro')
    expect(screen.getByTestId('theme-system').textContent).toBe('Tema: Sistema')
  })
})
