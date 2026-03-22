import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import React from 'react'

expect.extend(toHaveNoViolations)

vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({ t: (key) => key }),
}))

import SplashScreen from './SplashScreen'

describe('SplashScreen', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    // Default: no reduced motion
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders logo, title, and loading text', () => {
    render(<SplashScreen />)
    expect(screen.getByText('4D')).toBeInTheDocument()
    expect(screen.getByText('Yantra4D')).toBeInTheDocument()
    expect(screen.getByText('splash.loading')).toBeInTheDocument()
  })

  it('has role="status"', () => {
    render(<SplashScreen />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('does not show tips initially', () => {
    render(<SplashScreen />)
    expect(screen.queryByText(/splash\.tip_/)).not.toBeInTheDocument()
  })

  it('shows tips after 800ms delay', () => {
    render(<SplashScreen />)
    act(() => { vi.advanceTimersByTime(800) })
    // One of the tip keys should now be visible
    const tipEl = screen.getByText(/splash\.tip_\d+/)
    expect(tipEl).toBeInTheDocument()
  })

  it('rotates tips every 4s', () => {
    render(<SplashScreen />)
    act(() => { vi.advanceTimersByTime(800) })
    const firstTip = screen.getByText(/splash\.tip_\d+/).textContent

    // Advance past the fade-out (200ms) + interval (4000ms)
    act(() => { vi.advanceTimersByTime(4000) })
    act(() => { vi.advanceTimersByTime(200) })
    const secondTip = screen.getByText(/splash\.tip_\d+/).textContent

    // Tips should have changed (different index in rotation)
    expect(secondTip).not.toBe(firstTip)
  })

  it('shows static tip with reduced motion', () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(query => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    })

    render(<SplashScreen />)
    act(() => { vi.advanceTimersByTime(800) })
    const tip = screen.getByText(/splash\.tip_\d+/).textContent

    // Advance time — tip should NOT rotate
    act(() => { vi.advanceTimersByTime(8000) })
    expect(screen.getByText(/splash\.tip_\d+/).textContent).toBe(tip)
  })

  it('applies exit transition when exiting prop is true', () => {
    render(<SplashScreen exiting />)
    const container = screen.getByRole('status')
    expect(container.className).toContain('opacity-0')
  })

  it('does not have exit class when not exiting', () => {
    render(<SplashScreen />)
    const container = screen.getByRole('status')
    expect(container.className).toContain('opacity-100')
    expect(container.className).not.toContain('opacity-0')
  })

  it('has no accessibility violations', async () => {
    vi.useRealTimers()
    const { container } = render(<SplashScreen />)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  it('cleans up interval on unmount', () => {
    const clearSpy = vi.spyOn(globalThis, 'clearInterval')
    const { unmount } = render(<SplashScreen />)
    act(() => { vi.advanceTimersByTime(800) })
    unmount()
    expect(clearSpy).toHaveBeenCalled()
    clearSpy.mockRestore()
  })
})
