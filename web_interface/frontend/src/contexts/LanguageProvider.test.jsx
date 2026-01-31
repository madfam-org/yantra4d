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

function TestI18nKeys() {
  const { t } = useLanguage()
  return (
    <div>
      <span data-testid="error-title">{t('error.title')}</span>
      <span data-testid="error-retry">{t('error.retry')}</span>
      <span data-testid="nav-projects">{t('nav.projects')}</span>
      <span data-testid="viewer-hide">{t('viewer.hide_axes')}</span>
      <span data-testid="ctrl-wireframe">{t('ctrl.wireframe')}</span>
      <span data-testid="onboard-upload">{t('onboard.upload_title')}</span>
      <span data-testid="sr-toggle-lang">{t('sr.toggle_lang')}</span>
      <span data-testid="lang-en">{t('lang.switch_to_en')}</span>
      <span data-testid="lang-es">{t('lang.switch_to_es')}</span>
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

function TestPhase1Keys() {
  const { t } = useLanguage()
  return (
    <div>
      <span data-testid="act-share">{t('act.share')}</span>
      <span data-testid="act-share-copied">{t('act.share_copied')}</span>
      <span data-testid="act-undo">{t('act.undo')}</span>
      <span data-testid="act-redo">{t('act.redo')}</span>
      <span data-testid="act-format">{t('act.format')}</span>
      <span data-testid="print-title">{t('print.title')}</span>
      <span data-testid="print-material">{t('print.material')}</span>
      <span data-testid="print-time">{t('print.time')}</span>
      <span data-testid="print-weight">{t('print.weight')}</span>
      <span data-testid="print-cost">{t('print.cost')}</span>
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
    expect(localStorage.getItem('qubic-lang')).toBe('en')
    expect(screen.getByTestId('text').textContent).toBe('Generate')
  })

  it('reads default language from localStorage', () => {
    localStorage.setItem('qubic-lang', 'en')
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

  it('has i18n keys for error, nav, viewer, controls, and onboarding in English', () => {
    render(
      <LanguageProvider defaultLanguage="en">
        <TestI18nKeys />
      </LanguageProvider>
    )
    expect(screen.getByTestId('error-title').textContent).toBe('Something went wrong')
    expect(screen.getByTestId('error-retry').textContent).toBe('Try Again')
    expect(screen.getByTestId('nav-projects').textContent).toBe('Projects')
    expect(screen.getByTestId('viewer-hide').textContent).toBe('Hide axes')
    expect(screen.getByTestId('ctrl-wireframe').textContent).toBe('Wireframe')
    expect(screen.getByTestId('onboard-upload').textContent).toBe('Upload SCAD Files')
    expect(screen.getByTestId('sr-toggle-lang').textContent).toBe('Toggle Language')
    expect(screen.getByTestId('lang-en').textContent).toBe('English')
    expect(screen.getByTestId('lang-es').textContent).toBe('Español')
  })

  it('has i18n keys for error, nav, viewer, controls, and onboarding in Spanish', () => {
    render(
      <LanguageProvider defaultLanguage="es">
        <TestI18nKeys />
      </LanguageProvider>
    )
    expect(screen.getByTestId('error-title').textContent).toBe('Algo salió mal')
    expect(screen.getByTestId('error-retry').textContent).toBe('Intentar de Nuevo')
    expect(screen.getByTestId('nav-projects').textContent).toBe('Proyectos')
    expect(screen.getByTestId('viewer-hide').textContent).toBe('Ocultar ejes')
    expect(screen.getByTestId('ctrl-wireframe').textContent).toBe('Estructura')
    expect(screen.getByTestId('onboard-upload').textContent).toBe('Subir Archivos SCAD')
    expect(screen.getByTestId('sr-toggle-lang').textContent).toBe('Cambiar Idioma')
    expect(screen.getByTestId('lang-en').textContent).toBe('English')
    expect(screen.getByTestId('lang-es').textContent).toBe('Español')
  })

  it('has Phase 1 translation keys (share, undo/redo, format, print) in English', () => {
    render(
      <LanguageProvider defaultLanguage="en">
        <TestPhase1Keys />
      </LanguageProvider>
    )
    expect(screen.getByTestId('act-share').textContent).toBe('Share configuration')
    expect(screen.getByTestId('act-share-copied').textContent).toBe('Link copied!')
    expect(screen.getByTestId('act-undo').textContent).toBe('Undo')
    expect(screen.getByTestId('act-redo').textContent).toBe('Redo')
    expect(screen.getByTestId('act-format').textContent).toBe('Format')
    expect(screen.getByTestId('print-title').textContent).toBe('Print Estimate')
    expect(screen.getByTestId('print-material').textContent).toBe('Material')
    expect(screen.getByTestId('print-time').textContent).toBe('Time')
    expect(screen.getByTestId('print-weight').textContent).toBe('Weight')
    expect(screen.getByTestId('print-cost').textContent).toBe('Cost')
  })

  it('has Phase 1 translation keys (share, undo/redo, format, print) in Spanish', () => {
    render(
      <LanguageProvider defaultLanguage="es">
        <TestPhase1Keys />
      </LanguageProvider>
    )
    expect(screen.getByTestId('act-share').textContent).toBe('Compartir configuración')
    expect(screen.getByTestId('act-share-copied').textContent).toBe('¡Enlace copiado!')
    expect(screen.getByTestId('act-undo').textContent).toBe('Deshacer')
    expect(screen.getByTestId('act-redo').textContent).toBe('Rehacer')
    expect(screen.getByTestId('act-format').textContent).toBe('Formato')
    expect(screen.getByTestId('print-title').textContent).toBe('Estimación de Impresión')
    expect(screen.getByTestId('print-material').textContent).toBe('Material')
    expect(screen.getByTestId('print-time').textContent).toBe('Tiempo')
    expect(screen.getByTestId('print-weight').textContent).toBe('Peso')
    expect(screen.getByTestId('print-cost').textContent).toBe('Costo')
  })
})
