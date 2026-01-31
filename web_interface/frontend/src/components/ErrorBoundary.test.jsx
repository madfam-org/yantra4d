import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ErrorBoundary } from './ErrorBoundary'

// Suppress React error boundary console output during tests
vi.spyOn(console, 'error').mockImplementation(() => {})

const mockT = (key) => {
  const translations = {
    'error.title': 'Something went wrong',
    'error.fallback': 'An unexpected error occurred',
    'error.retry': 'Try Again',
  }
  return translations[key] || key
}

function ThrowingChild({ message }) {
  throw new Error(message)
}

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary t={mockT}>
        <div>Hello</div>
      </ErrorBoundary>
    )
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('shows error message when child throws', () => {
    render(
      <ErrorBoundary t={mockT}>
        <ThrowingChild message="test error" />
      </ErrorBoundary>
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByText('test error')).toBeInTheDocument()
  })

  it('reset button clears the error', () => {
    const { rerender } = render(
      <ErrorBoundary t={mockT}>
        <ThrowingChild message="boom" />
      </ErrorBoundary>
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()

    screen.getByText('Try Again').click()

    // After reset, re-render with non-throwing child
    rerender(
      <ErrorBoundary t={mockT}>
        <div>Recovered</div>
      </ErrorBoundary>
    )
    expect(screen.getByText('Recovered')).toBeInTheDocument()
  })

  it('falls back to key identity when no t prop provided', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild message="no t prop" />
      </ErrorBoundary>
    )
    // Without t prop, it renders the key itself
    expect(screen.getByText('error.title')).toBeInTheDocument()
    expect(screen.getByText('error.retry')).toBeInTheDocument()
  })
})
