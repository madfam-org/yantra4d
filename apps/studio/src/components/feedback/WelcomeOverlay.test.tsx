import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({ language: 'en', t: (k: string) => k }),
}))

import WelcomeOverlay from './WelcomeOverlay'

const WELCOME_DATA = {
  enabled: true,
  heading: { en: 'Welcome to Test', es: 'Bienvenido' },
  body: { en: 'A test project description.', es: 'Descripción de prueba.' },
  features: [
    { icon: '🎚️', text: { en: 'Drag sliders to customize', es: 'Arrastra controles' } },
    { icon: '📥', text: { en: 'Download your STL', es: 'Descarga tu STL' } },
  ],
  cta_label: { en: 'Get Started', es: 'Comenzar' },
}

beforeEach(() => {
  localStorage.clear()
})

describe('WelcomeOverlay', () => {
  it('renders heading, body, features, and CTA', () => {
    render(<WelcomeOverlay slug="test" welcome={WELCOME_DATA} />)
    expect(screen.getByText('Welcome to Test')).toBeInTheDocument()
    expect(screen.getByText('A test project description.')).toBeInTheDocument()
    expect(screen.getByText('Drag sliders to customize')).toBeInTheDocument()
    expect(screen.getByText('Download your STL')).toBeInTheDocument()
    expect(screen.getByTestId('welcome-cta')).toHaveTextContent('Get Started')
  })

  it('dismisses on CTA click and persists to localStorage', () => {
    render(<WelcomeOverlay slug="test" welcome={WELCOME_DATA} />)
    expect(screen.getByText('Welcome to Test')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('welcome-cta'))
    expect(screen.queryByText('Welcome to Test')).not.toBeInTheDocument()
    expect(localStorage.getItem('yantra4d-welcome-test')).toBe('true')
  })

  it('dismisses on Escape key', () => {
    render(<WelcomeOverlay slug="test" welcome={WELCOME_DATA} />)
    expect(screen.getByText('Welcome to Test')).toBeInTheDocument()

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByText('Welcome to Test')).not.toBeInTheDocument()
    expect(localStorage.getItem('yantra4d-welcome-test')).toBe('true')
  })

  it('does not render if already dismissed', () => {
    localStorage.setItem('yantra4d-welcome-test', 'true')
    render(<WelcomeOverlay slug="test" welcome={WELCOME_DATA} />)
    expect(screen.queryByText('Welcome to Test')).not.toBeInTheDocument()
  })

  it('renders with minimal config (no features, no body)', () => {
    render(<WelcomeOverlay slug="test" welcome={{ heading: { en: 'Hello' } }} />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
    expect(screen.getByTestId('welcome-cta')).toHaveTextContent('Get Started')
  })

  it('uses per-project localStorage keys', () => {
    localStorage.setItem('yantra4d-welcome-other-project', 'true')
    render(<WelcomeOverlay slug="test" welcome={WELCOME_DATA} />)
    // Should still show for "test" even though "other-project" is dismissed
    expect(screen.getByText('Welcome to Test')).toBeInTheDocument()
  })

  it('has proper accessibility attributes', () => {
    render(<WelcomeOverlay slug="test" welcome={WELCOME_DATA} />)
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveAttribute('aria-labelledby', 'welcome-heading')
  })
})
