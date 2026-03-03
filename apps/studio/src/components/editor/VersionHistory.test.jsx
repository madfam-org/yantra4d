import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({ t: (key) => key }),
}))

import VersionHistory from './VersionHistory'

describe('VersionHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state initially', () => {
    globalThis.fetch = vi.fn(() => new Promise(() => {})) // never resolves
    render(<VersionHistory projectSlug="test" onClose={vi.fn()} />)
    expect(screen.getByTestId('version-history')).toBeInTheDocument()
  })

  it('renders commits after fetch', async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          commits: [
            { hash: 'abc123def456', short_hash: 'abc123d', author: 'Test User', date: '2024-01-15T10:30:00', message: 'Initial commit' },
            { hash: 'def456ghi789', short_hash: 'def456g', author: 'Test User', date: '2024-01-14T09:00:00', message: 'Add feature' },
          ],
        }),
      })
    )

    render(<VersionHistory projectSlug="test" onClose={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText('Initial commit')).toBeInTheDocument()
      expect(screen.getByText('Add feature')).toBeInTheDocument()
    })
  })

  it('renders error state on fetch failure', async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 404,
        json: () => Promise.resolve({}),
      })
    )

    render(<VersionHistory projectSlug="test" onClose={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText('HTTP 404')).toBeInTheDocument()
    })
  })

  it('renders empty state when no commits', async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ commits: [] }),
      })
    )

    render(<VersionHistory projectSlug="test" onClose={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText('No commits found.')).toBeInTheDocument()
    })
  })

  it('calls onClose when close button is clicked', () => {
    globalThis.fetch = vi.fn(() => new Promise(() => {}))
    const onClose = vi.fn()
    render(<VersionHistory projectSlug="test" onClose={onClose} />)
    fireEvent.click(screen.getByLabelText('Close history'))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('toggles commit selection on click', async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          commits: [
            { hash: 'abc123', short_hash: 'abc123', author: 'User', date: '2024-01-15', message: 'Test' },
          ],
        }),
      })
    )

    render(<VersionHistory projectSlug="test" onClose={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText('Test')).toBeInTheDocument()
    })

    const commitBtn = screen.getByText('Test').closest('button')
    fireEvent.click(commitBtn)
    expect(commitBtn.getAttribute('aria-pressed')).toBe('true')

    fireEvent.click(commitBtn)
    expect(commitBtn.getAttribute('aria-pressed')).toBe('false')
  })
})
