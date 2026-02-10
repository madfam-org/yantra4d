import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'

const mockApiFetch = vi.fn()

vi.mock('../../services/apiClient', () => ({
  apiFetch: (...args) => mockApiFetch(...args),
}))

vi.mock('../../services/backendDetection', () => ({
  getApiBase: () => 'http://localhost:5000',
}))

import GitHubImportWizard from './GitHubImportWizard'

const defaultProps = {
  onClose: vi.fn(),
  onImported: vi.fn(),
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('GitHubImportWizard', () => {
  it('renders step 1: URL input', () => {
    render(<GitHubImportWizard {...defaultProps} />)
    expect(screen.getByText('Import from GitHub')).toBeInTheDocument()
    expect(screen.getByLabelText('Repository URL')).toBeInTheDocument()
    expect(screen.getByText('Validate')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('disables validate button when URL is empty', () => {
    render(<GitHubImportWizard {...defaultProps} />)
    expect(screen.getByText('Validate')).toBeDisabled()
  })

  it('enables validate button when URL is entered', () => {
    render(<GitHubImportWizard {...defaultProps} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), {
      target: { value: 'https://github.com/user/repo' },
    })
    expect(screen.getByText('Validate')).not.toBeDisabled()
  })

  it('calls onClose when clicking cancel', () => {
    render(<GitHubImportWizard {...defaultProps} />)
    fireEvent.click(screen.getByText('Cancel'))
    expect(defaultProps.onClose).toHaveBeenCalledOnce()
  })

  it('shows validation error on failed response', async () => {
    mockApiFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Repository not found' }),
    })
    render(<GitHubImportWizard {...defaultProps} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), {
      target: { value: 'https://github.com/user/nonexistent' },
    })
    fireEvent.click(screen.getByText('Validate'))

    await waitFor(() => {
      expect(screen.getByText('Repository not found')).toBeInTheDocument()
    })
  })

  it('shows network error on fetch failure', async () => {
    mockApiFetch.mockRejectedValue(new Error('Network error'))
    render(<GitHubImportWizard {...defaultProps} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), {
      target: { value: 'https://github.com/user/repo' },
    })
    fireEvent.click(screen.getByText('Validate'))

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('advances to step 2 on successful validation', async () => {
    mockApiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        scad_files: [{ path: 'main.scad', size: 2048 }],
        has_manifest: true,
        manifest: { project: { name: 'Test' } },
      }),
    })
    render(<GitHubImportWizard {...defaultProps} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), {
      target: { value: 'https://github.com/user/my-repo' },
    })
    fireEvent.click(screen.getByText('Validate'))

    await waitFor(() => {
      expect(screen.getByLabelText('Project slug')).toBeInTheDocument()
    })
    // Shows detected files
    expect(screen.getByText(/Detected files \(1\)/)).toBeInTheDocument()
    expect(screen.getByText(/main\.scad/)).toBeInTheDocument()
    // Shows found manifest message
    expect(screen.getByText(/Found project\.json in repository/)).toBeInTheDocument()
    // Auto-generates slug from repo URL
    expect(screen.getByLabelText('Project slug')).toHaveValue('my-repo')
    // Shows Back and Import buttons
    expect(screen.getByText('Back')).toBeInTheDocument()
    expect(screen.getByText('Import')).toBeInTheDocument()
  })

  it('shows warning when no manifest found', async () => {
    mockApiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        scad_files: [{ path: 'main.scad', size: 2048 }],
        has_manifest: false,
        manifest: null,
      }),
    })
    render(<GitHubImportWizard {...defaultProps} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), {
      target: { value: 'https://github.com/user/repo' },
    })
    fireEvent.click(screen.getByText('Validate'))

    await waitFor(() => {
      expect(screen.getByText(/No project\.json found/)).toBeInTheDocument()
    })
  })

  it('goes back to step 1 when clicking Back', async () => {
    mockApiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        scad_files: [{ path: 'main.scad', size: 1024 }],
        has_manifest: true,
        manifest: { project: { name: 'Test' } },
      }),
    })
    render(<GitHubImportWizard {...defaultProps} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), {
      target: { value: 'https://github.com/user/repo' },
    })
    fireEvent.click(screen.getByText('Validate'))

    await waitFor(() => {
      expect(screen.getByText('Back')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Back'))
    expect(screen.getByLabelText('Repository URL')).toBeInTheDocument()
  })

  it('shows error when importing without manifest', async () => {
    // First validate with no manifest
    mockApiFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        scad_files: [{ path: 'main.scad', size: 1024 }],
        has_manifest: false,
        manifest: null,
      }),
    })
    render(<GitHubImportWizard {...defaultProps} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), {
      target: { value: 'https://github.com/user/repo' },
    })
    fireEvent.click(screen.getByText('Validate'))

    await waitFor(() => {
      expect(screen.getByText('Import')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('Import'))

    await waitFor(() => {
      expect(screen.getByText('A valid manifest is required to import')).toBeInTheDocument()
    })
  })

  it('advances to step 3 on successful import', async () => {
    // Validate
    mockApiFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        scad_files: [{ path: 'main.scad', size: 1024 }],
        has_manifest: true,
        manifest: { project: { name: 'Test' } },
      }),
    })
    render(<GitHubImportWizard {...defaultProps} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), {
      target: { value: 'https://github.com/user/repo' },
    })
    fireEvent.click(screen.getByText('Validate'))

    await waitFor(() => {
      expect(screen.getByText('Import')).toBeInTheDocument()
    })

    // Import
    mockApiFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ slug: 'repo' }),
    })
    fireEvent.click(screen.getByText('Import'))

    await waitFor(() => {
      expect(screen.getByText('Project imported')).toBeInTheDocument()
    })
    expect(defaultProps.onImported).toHaveBeenCalledWith('repo')
    expect(screen.getByText('Open in Editor')).toBeInTheDocument()
  })

  it('shows loading state during validation', async () => {
    mockApiFetch.mockImplementation(() => new Promise(() => {})) // never resolves
    render(<GitHubImportWizard {...defaultProps} />)
    fireEvent.change(screen.getByLabelText('Repository URL'), {
      target: { value: 'https://github.com/user/repo' },
    })
    fireEvent.click(screen.getByText('Validate'))

    await waitFor(() => {
      expect(screen.getByText('Validating...')).toBeInTheDocument()
    })
  })
})
