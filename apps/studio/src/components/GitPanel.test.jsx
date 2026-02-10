import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'

const mockGetStatus = vi.fn()
const mockGetDiff = vi.fn()
const mockCommit = vi.fn()
const mockPush = vi.fn()
const mockPull = vi.fn()
const mockConnectRemote = vi.fn()

vi.mock('../services/gitService', () => ({
  getStatus: (...args) => mockGetStatus(...args),
  getDiff: (...args) => mockGetDiff(...args),
  commit: (...args) => mockCommit(...args),
  push: (...args) => mockPush(...args),
  pull: (...args) => mockPull(...args),
  connectRemote: (...args) => mockConnectRemote(...args),
}))

import GitPanel from './GitPanel'

const cleanStatus = {
  branch: 'main',
  clean: true,
  remote: 'origin',
  ahead: 0,
  behind: 0,
  modified: [],
  added: [],
  deleted: [],
  untracked: [],
}

const dirtyStatus = {
  branch: 'main',
  clean: false,
  remote: 'origin',
  ahead: 0,
  behind: 0,
  modified: ['model.scad'],
  added: [],
  deleted: [],
  untracked: ['new-file.scad'],
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.useFakeTimers({ shouldAdvanceTime: true })
  mockGetDiff.mockResolvedValue({ diff: '' })
})

afterEach(() => {
  vi.useRealTimers()
})

describe('GitPanel', () => {
  it('displays branch name after loading', async () => {
    mockGetStatus.mockResolvedValue(cleanStatus)
    render(<GitPanel slug="test-project" />)
    await waitFor(() => {
      expect(screen.getByText('main')).toBeInTheDocument()
    })
  })

  it('shows clean status indicator', async () => {
    mockGetStatus.mockResolvedValue(cleanStatus)
    render(<GitPanel slug="test-project" />)
    await waitFor(() => {
      expect(screen.getByText('Clean')).toBeInTheDocument()
    })
  })

  it('shows changed file count when dirty', async () => {
    mockGetStatus.mockResolvedValue(dirtyStatus)
    mockGetDiff.mockResolvedValue({ diff: '--- a/model.scad\n+++ b/model.scad' })
    render(<GitPanel slug="test-project" />)
    await waitFor(() => {
      expect(screen.getByText('2 changed')).toBeInTheDocument()
    })
  })

  it('lists changed files with checkboxes', async () => {
    mockGetStatus.mockResolvedValue(dirtyStatus)
    mockGetDiff.mockResolvedValue({ diff: 'diff content' })
    render(<GitPanel slug="test-project" />)
    await waitFor(() => {
      expect(screen.getByText('model.scad')).toBeInTheDocument()
      expect(screen.getByText('new-file.scad')).toBeInTheDocument()
    })
    // Both should be checked by default
    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes).toHaveLength(2)
    checkboxes.forEach(cb => expect(cb).toBeChecked())
  })

  it('toggles file selection', async () => {
    mockGetStatus.mockResolvedValue(dirtyStatus)
    mockGetDiff.mockResolvedValue({ diff: '' })
    render(<GitPanel slug="test-project" />)
    await waitFor(() => {
      expect(screen.getByText('model.scad')).toBeInTheDocument()
    })
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0])
    expect(checkboxes[0]).not.toBeChecked()
  })

  it('shows file status indicators (M for modified, ? for untracked)', async () => {
    mockGetStatus.mockResolvedValue(dirtyStatus)
    mockGetDiff.mockResolvedValue({ diff: '' })
    render(<GitPanel slug="test-project" />)
    await waitFor(() => {
      expect(screen.getByText('M')).toBeInTheDocument()
      expect(screen.getByText('?')).toBeInTheDocument()
    })
  })

  it('shows commit input when files changed', async () => {
    mockGetStatus.mockResolvedValue(dirtyStatus)
    mockGetDiff.mockResolvedValue({ diff: '' })
    render(<GitPanel slug="test-project" />)
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Commit message...')).toBeInTheDocument()
    })
  })

  it('disables commit button when message is empty', async () => {
    mockGetStatus.mockResolvedValue(dirtyStatus)
    mockGetDiff.mockResolvedValue({ diff: '' })
    render(<GitPanel slug="test-project" />)
    await waitFor(() => {
      expect(screen.getByText('Commit')).toBeInTheDocument()
    })
    expect(screen.getByText('Commit').closest('button')).toBeDisabled()
  })

  it('performs commit action', async () => {
    mockGetStatus.mockResolvedValue(dirtyStatus)
    mockGetDiff.mockResolvedValue({ diff: '' })
    mockCommit.mockResolvedValue({})
    render(<GitPanel slug="test-project" />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Commit message...')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByPlaceholderText('Commit message...'), {
      target: { value: 'Add new part' },
    })
    fireEvent.click(screen.getByText('Commit').closest('button'))

    await waitFor(() => {
      expect(mockCommit).toHaveBeenCalledWith(
        'test-project',
        'Add new part',
        expect.arrayContaining(['model.scad', 'new-file.scad'])
      )
    })
  })

  it('shows success message after commit', async () => {
    mockGetStatus
      .mockResolvedValueOnce(dirtyStatus)
      .mockResolvedValue(cleanStatus)
    mockGetDiff.mockResolvedValue({ diff: '' })
    mockCommit.mockResolvedValue({})
    render(<GitPanel slug="test-project" />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Commit message...')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByPlaceholderText('Commit message...'), {
      target: { value: 'Fix bug' },
    })
    fireEvent.click(screen.getByText('Commit').closest('button'))

    await waitFor(() => {
      expect(screen.getByText('Committed')).toBeInTheDocument()
    })
  })

  it('shows error on commit failure', async () => {
    mockGetStatus.mockResolvedValue(dirtyStatus)
    mockGetDiff.mockResolvedValue({ diff: '' })
    mockCommit.mockRejectedValue(new Error('Permission denied'))
    render(<GitPanel slug="test-project" />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Commit message...')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByPlaceholderText('Commit message...'), {
      target: { value: 'Test' },
    })
    fireEvent.click(screen.getByText('Commit').closest('button'))

    await waitFor(() => {
      expect(screen.getByText('Permission denied')).toBeInTheDocument()
    })
  })

  it('has push and pull buttons with screen reader labels', async () => {
    mockGetStatus.mockResolvedValue(cleanStatus)
    render(<GitPanel slug="test-project" />)
    await waitFor(() => {
      expect(screen.getByText('Push')).toBeInTheDocument()
      expect(screen.getByText('Pull')).toBeInTheDocument()
      expect(screen.getByText('Refresh')).toBeInTheDocument()
    })
  })

  it('performs push action', async () => {
    mockGetStatus.mockResolvedValue(cleanStatus)
    mockPush.mockResolvedValue({})
    render(<GitPanel slug="test-project" />)

    await waitFor(() => {
      expect(screen.getByText('main')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTitle('Push'))
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('test-project')
    })
  })

  it('performs pull action', async () => {
    mockGetStatus.mockResolvedValue(cleanStatus)
    mockPull.mockResolvedValue({})
    render(<GitPanel slug="test-project" />)

    await waitFor(() => {
      expect(screen.getByText('main')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTitle('Pull'))
    await waitFor(() => {
      expect(mockPull).toHaveBeenCalledWith('test-project')
    })
  })

  it('shows connect remote form when no remote', async () => {
    mockGetStatus.mockResolvedValue({ ...cleanStatus, remote: null })
    render(<GitPanel slug="test-project" />)

    await waitFor(() => {
      expect(screen.getByText('Connect to GitHub')).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/github\.com/)).toBeInTheDocument()
    })
  })

  it('disables push/pull when no remote', async () => {
    mockGetStatus.mockResolvedValue({ ...cleanStatus, remote: null })
    render(<GitPanel slug="test-project" />)

    await waitFor(() => {
      const buttons = screen.getAllByTitle(/Connect to GitHub first/)
      expect(buttons).toHaveLength(2)
      buttons.forEach(btn => expect(btn).toBeDisabled())
    })
  })

  it('performs connect remote action', async () => {
    mockGetStatus
      .mockResolvedValueOnce({ ...cleanStatus, remote: null })
      .mockResolvedValue(cleanStatus)
    mockConnectRemote.mockResolvedValue({})
    render(<GitPanel slug="test-project" />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/github\.com/)).toBeInTheDocument()
    })

    fireEvent.change(screen.getByPlaceholderText(/github\.com/), {
      target: { value: 'https://github.com/user/repo.git' },
    })
    fireEvent.click(screen.getByText('Connect'))

    await waitFor(() => {
      expect(mockConnectRemote).toHaveBeenCalledWith('test-project', 'https://github.com/user/repo.git')
    })
  })

  it('commits on Enter key in commit input', async () => {
    mockGetStatus.mockResolvedValue(dirtyStatus)
    mockGetDiff.mockResolvedValue({ diff: '' })
    mockCommit.mockResolvedValue({})
    render(<GitPanel slug="test-project" />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Commit message...')).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText('Commit message...')
    fireEvent.change(input, { target: { value: 'Quick fix' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => {
      expect(mockCommit).toHaveBeenCalledWith('test-project', 'Quick fix', expect.any(Array))
    })
  })

  it('connects remote on Enter key in remote URL input', async () => {
    mockGetStatus.mockResolvedValueOnce({ ...cleanStatus, remote: null }).mockResolvedValue(cleanStatus)
    mockConnectRemote.mockResolvedValue({})
    render(<GitPanel slug="test-project" />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/github\.com/)).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/github\.com/)
    fireEvent.change(input, { target: { value: 'https://github.com/user/repo.git' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => {
      expect(mockConnectRemote).toHaveBeenCalled()
    })
  })

  it('shows error on connect remote failure', async () => {
    mockGetStatus.mockResolvedValue({ ...cleanStatus, remote: null })
    mockConnectRemote.mockRejectedValue(new Error('Auth failed'))
    render(<GitPanel slug="test-project" />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/github\.com/)).toBeInTheDocument()
    })

    fireEvent.change(screen.getByPlaceholderText(/github\.com/), {
      target: { value: 'https://github.com/user/repo.git' },
    })
    fireEvent.click(screen.getByText('Connect'))

    await waitFor(() => {
      expect(screen.getByText('Auth failed')).toBeInTheDocument()
    })
  })

  it('shows ahead/behind indicators', async () => {
    mockGetStatus.mockResolvedValue({ ...cleanStatus, ahead: 2, behind: 1 })
    render(<GitPanel slug="test-project" />)
    await waitFor(() => {
      expect(screen.getByText('2 ahead')).toBeInTheDocument()
      expect(screen.getByText('1 behind')).toBeInTheDocument()
    })
  })

  it('shows diff preview when diff exists', async () => {
    mockGetStatus.mockResolvedValue(dirtyStatus)
    mockGetDiff.mockResolvedValue({ diff: '+new line\n-old line' })
    render(<GitPanel slug="test-project" />)
    await waitFor(() => {
      expect(screen.getByText('Diff preview')).toBeInTheDocument()
    })
  })

  it('shows error when status fetch fails', async () => {
    mockGetStatus.mockRejectedValue(new Error('Server unavailable'))
    render(<GitPanel slug="test-project" />)
    await waitFor(() => {
      expect(screen.getByText('Server unavailable')).toBeInTheDocument()
    })
  })
})
