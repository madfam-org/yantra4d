import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, afterEach } from 'vitest'
import GitHubImportWizard from './GitHubImportWizard'

// Mock API client
vi.mock('../../services/apiClient', () => ({
  apiFetch: vi.fn()
}))
import { apiFetch } from '../../services/apiClient'

describe('GitHubImportWizard', () => {
  const mockOnClose = vi.fn()
  const mockOnImported = vi.fn()

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders initial URL input step', () => {
    render(<GitHubImportWizard onClose={mockOnClose} />)
    expect(screen.getByText('Import from GitHub')).toBeInTheDocument()
    expect(screen.getByLabelText('Repository URL')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Validate' })).toBeDisabled()
  })

  it('enables validate button when URL is entered', () => {
    render(<GitHubImportWizard onClose={mockOnClose} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), { target: { value: 'https://github.com/user/repo' } })
    expect(screen.getByRole('button', { name: 'Validate' })).toBeEnabled()
  })

  it('handles validation success and advances to step 2', async () => {
    // Mock API response
    apiFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        scad_files: [{ path: 'main.scad', size: 1024 }],
        has_manifest: true,
        manifest: { name: 'Test Project' }
      })
    })

    render(<GitHubImportWizard onClose={mockOnClose} />)

    // Enter URL
    fireEvent.change(screen.getByLabelText('Repository URL'), { target: { value: 'https://github.com/user/valid-repo' } })

    // Click Validate
    fireEvent.click(screen.getByRole('button', { name: 'Validate' }))

    // Expect loading state
    expect(screen.getByText('Validating...')).toBeInTheDocument()

    // Wait for step 2
    await waitFor(() => {
      expect(screen.getByText('Project slug')).toBeInTheDocument()
    })

    // Verify slug generation
    expect(screen.getByLabelText('Project slug')).toHaveValue('valid-repo')
    expect(screen.getByText('Found project.json in repository')).toBeInTheDocument()
  })

  it('handles validation failure', async () => {
    apiFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'Repo used not found' })
    })

    render(<GitHubImportWizard onClose={mockOnClose} />)

    fireEvent.change(screen.getByLabelText('Repository URL'), { target: { value: 'https://github.com/bad/repo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Validate' }))

    expect(await screen.findByText('Repo used not found')).toBeInTheDocument()
    // Should still be on step 1
    expect(screen.getByLabelText('Repository URL')).toBeInTheDocument()
  })

  it('handles import success', async () => {
    // Stage 1: Validation
    apiFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        scad_files: [],
        has_manifest: true,
        manifest: {}
      })
    })

    render(<GitHubImportWizard onClose={mockOnClose} onImported={mockOnImported} />)

    fireEvent.change(screen.getByLabelText('Repository URL'), { target: { value: 'https://github.com/u/r' } })
    fireEvent.click(screen.getByRole('button', { name: 'Validate' }))

    await waitFor(() => screen.getByLabelText('Project slug'))

    // Stage 2: Import
    apiFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ slug: 'r' })
    })

    fireEvent.click(screen.getByRole('button', { name: 'Import' }))

    expect(await screen.findByText('Project imported')).toBeInTheDocument()
    expect(mockOnImported).toHaveBeenCalledWith('r')

    // Verify opening editor
    fireEvent.click(screen.getByRole('button', { name: 'Open in Editor' }))
    expect(mockOnClose).toHaveBeenCalled()
  })

  it('handles validation network error', async () => {
    apiFetch.mockRejectedValueOnce(new Error('Network error'))
    render(<GitHubImportWizard onClose={mockOnClose} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), { target: { value: 'https://github.com/bad/repo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Validate' }))
    expect(await screen.findByText('Network error')).toBeInTheDocument()
  })

  it('handles import without manifest', async () => {
    apiFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        scad_files: [],
        has_manifest: false
      })
    })
    render(<GitHubImportWizard onClose={mockOnClose} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), { target: { value: 'https://github.com/u/r' } })
    fireEvent.click(screen.getByRole('button', { name: 'Validate' }))
    await waitFor(() => screen.getByLabelText('Project slug'))

    // Attempt import
    fireEvent.click(screen.getByRole('button', { name: 'Import' }))
    expect(await screen.findByText('A valid manifest is required to import')).toBeInTheDocument()
  })

  it('handles import error response', async () => {
    apiFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        scad_files: [],
        has_manifest: true,
        manifest: {}
      })
    })
    render(<GitHubImportWizard onClose={mockOnClose} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), { target: { value: 'https://github.com/u/r' } })
    fireEvent.click(screen.getByRole('button', { name: 'Validate' }))
    await waitFor(() => screen.getByLabelText('Project slug'))

    apiFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'Import failed' })
    })
    fireEvent.click(screen.getByRole('button', { name: 'Import' }))
    expect(await screen.findByText('Import failed')).toBeInTheDocument()
  })

  it('handles import network error', async () => {
    apiFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        scad_files: [],
        has_manifest: true,
        manifest: {}
      })
    })
    render(<GitHubImportWizard onClose={mockOnClose} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), { target: { value: 'https://github.com/u/r' } })
    fireEvent.click(screen.getByRole('button', { name: 'Validate' }))
    await waitFor(() => screen.getByLabelText('Project slug'))

    apiFetch.mockRejectedValueOnce(new Error('Network import error'))
    fireEvent.click(screen.getByRole('button', { name: 'Import' }))
    expect(await screen.findByText('Network import error')).toBeInTheDocument()
  })

  it('allows user to navigate back', async () => {
    apiFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        scad_files: [],
        has_manifest: true,
        manifest: {}
      })
    })
    render(<GitHubImportWizard onClose={mockOnClose} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), { target: { value: 'https://github.com/u/r' } })
    fireEvent.click(screen.getByRole('button', { name: 'Validate' }))
    await waitFor(() => screen.getByLabelText('Project slug'))

    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByRole('button', { name: 'Validate' })).toBeInTheDocument()
  })

  it('allows user to modify slug', async () => {
    apiFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        scad_files: [],
        has_manifest: true,
        manifest: {}
      })
    })
    render(<GitHubImportWizard onClose={mockOnClose} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), { target: { value: 'https://github.com/u/custom-repo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Validate' }))
    await waitFor(() => screen.getByLabelText('Project slug'))

    const slugInput = screen.getByLabelText('Project slug')
    fireEvent.change(slugInput, { target: { value: 'New_SLUG-1' } })

    // verifies sanitization happens too
    expect(slugInput.value).toBe('new_slug-1')
  })
})
