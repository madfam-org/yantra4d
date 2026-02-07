import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ForkDialog from './ForkDialog'

vi.mock('../services/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

vi.mock('../services/apiClient', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../services/apiClient'

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
})
