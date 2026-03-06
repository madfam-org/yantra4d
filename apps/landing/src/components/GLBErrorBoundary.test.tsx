import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GLBErrorBoundary } from './GLBErrorBoundary'

function ThrowingChild() {
  throw new Error('GLB failed to load')
}

describe('GLBErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <GLBErrorBoundary fallback={<div>Error</div>}>
        <div>Content</div>
      </GLBErrorBoundary>
    )
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('renders fallback on error', () => {
    // Suppress console.error for expected error boundary
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <GLBErrorBoundary fallback={<div>Fallback Content</div>}>
        <ThrowingChild />
      </GLBErrorBoundary>
    )
    expect(screen.getByText('Fallback Content')).toBeInTheDocument()
    spy.mockRestore()
  })
})
