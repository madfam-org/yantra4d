import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ErrorBoundary } from './ErrorBoundary'

// Suppress React error boundary console output during tests
vi.spyOn(console, 'error').mockImplementation(() => {})

function ThrowingChild({ message }) {
  throw new Error(message)
}

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Hello</div>
      </ErrorBoundary>
    )
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('shows error message when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild message="test error" />
      </ErrorBoundary>
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByText('test error')).toBeInTheDocument()
  })

  it('reset button clears the error', () => {
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowingChild message="boom" />
      </ErrorBoundary>
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()

    screen.getByText('Try Again').click()

    // After reset, re-render with non-throwing child
    rerender(
      <ErrorBoundary>
        <div>Recovered</div>
      </ErrorBoundary>
    )
    expect(screen.getByText('Recovered')).toBeInTheDocument()
  })
})
