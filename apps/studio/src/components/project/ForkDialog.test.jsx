import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ForkDialog from './ForkDialog'

vi.mock('../../services/core/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('../../services/core/apiClient', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../../services/core/apiClient'

const defaultProps = {
  slug: 'gridfinity',
  projectName: 'Gridfinity Extended',
  onClose: vi.fn(),
  onForked: vi.fn(),
}

describe('ForkDialog', () => {
  it('renders with project name', () => {
    render(<ForkDialog {...defaultProps} />)
    expect(screen.getByText(/Gridfinity Extended/)).toBeInTheDocument()
  })

  it('pre-fills slug with my- prefix', () => {
    render(<ForkDialog {...defaultProps} />)
    const input = screen.getByLabelText(/project slug/i)
    expect(input.value).toBe('my-gridfinity')
  })

  it('has fork button', () => {
    render(<ForkDialog {...defaultProps} />)
    expect(screen.getByRole('button', { name: /fork & edit/i })).toBeInTheDocument()
  })

  it('has cancel button', () => {
    render(<ForkDialog {...defaultProps} />)
    const cancelBtn = screen.getByRole('button', { name: /cancel/i })
    fireEvent.click(cancelBtn)
    expect(defaultProps.onClose).toHaveBeenCalled()
  })

  it('calls API and onForked on success', async () => {
    apiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true, slug: 'my-gridfinity' }),
    })

    render(<ForkDialog {...defaultProps} />)
    fireEvent.click(screen.getByRole('button', { name: /fork & edit/i }))

    // Wait for async
    await vi.waitFor(() => {
      expect(defaultProps.onForked).toHaveBeenCalledWith('my-gridfinity')
    })
  })

  it('shows error on API failure', async () => {
    apiFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Already exists' }),
    })

    render(<ForkDialog {...defaultProps} />)
    fireEvent.click(screen.getByRole('button', { name: /fork & edit/i }))

    await vi.waitFor(() => {
      expect(screen.getByText('Already exists')).toBeInTheDocument()
    })
  })

  it('shows fallback error when API returns no error field', async () => {
    apiFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({}),
    })

    render(<ForkDialog {...defaultProps} />)
    fireEvent.click(screen.getByRole('button', { name: /fork & edit/i }))

    await vi.waitFor(() => {
      expect(screen.getByText('Fork failed')).toBeInTheDocument()
    })
  })

  it('shows error when fetch rejects (network error)', async () => {
    apiFetch.mockRejectedValue(new Error('Network down'))

    render(<ForkDialog {...defaultProps} />)
    fireEvent.click(screen.getByRole('button', { name: /fork & edit/i }))

    await vi.waitFor(() => {
      expect(screen.getByText('Network down')).toBeInTheDocument()
    })
  })

  it('sanitizes slug on input change', () => {
    render(<ForkDialog {...defaultProps} />)
    const input = screen.getByLabelText(/project slug/i)
    fireEvent.change(input, { target: { value: 'My NEW Project!' } })
    expect(input.value).toBe('my-new-project')
  })

  it('shows validation error for invalid slug', () => {
    render(<ForkDialog {...defaultProps} />)
    const input = screen.getByLabelText(/project slug/i)
    fireEvent.change(input, { target: { value: 'a' } })
    expect(screen.getByText(/3-50 chars/)).toBeInTheDocument()
  })

  it('does not show validation error when slug is empty', () => {
    render(<ForkDialog {...defaultProps} />)
    const input = screen.getByLabelText(/project slug/i)
    fireEvent.change(input, { target: { value: '' } })
    // The !isValid && newSlug check means empty slug doesn't show the message
    expect(screen.queryByText(/3-50 chars/)).not.toBeInTheDocument()
  })

  it('closes on Escape key in dialog', () => {
    render(<ForkDialog {...defaultProps} />)
    const dialog = screen.getByRole('dialog')
    fireEvent.keyDown(dialog, { key: 'Escape' })
    expect(defaultProps.onClose).toHaveBeenCalled()
  })

  it('closes on backdrop click', () => {
    const onClose = vi.fn()
    const { container } = render(<ForkDialog {...defaultProps} onClose={onClose} />)
    // Click the backdrop (outermost div)
    fireEvent.click(container.firstChild)
    expect(onClose).toHaveBeenCalled()
  })

  it('stops propagation on dialog click', () => {
    const onClose = vi.fn()
    render(<ForkDialog {...defaultProps} onClose={onClose} />)
    const dialog = screen.getByRole('dialog')
    fireEvent.click(dialog)
    // onClose should NOT be called since stopPropagation prevents it
    expect(onClose).not.toHaveBeenCalled()
  })
})
