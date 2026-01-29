import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { ThemeProvider, useTheme } from './ThemeProvider'

function TestConsumer() {
  const { theme, setTheme } = useTheme()
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button onClick={() => setTheme('dark')}>Dark</button>
    </div>
  )
}

describe('ThemeProvider', () => {
  beforeEach(() => localStorage.clear())

  it('defaults to system theme', () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    )
    expect(screen.getByTestId('theme').textContent).toBe('system')
  })

  it('setTheme updates theme and persists to localStorage', () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    )
    act(() => screen.getByText('Dark').click())
    expect(screen.getByTestId('theme').textContent).toBe('dark')
    expect(localStorage.getItem('vite-ui-theme')).toBe('dark')
  })
})
