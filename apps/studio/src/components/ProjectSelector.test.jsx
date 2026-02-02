import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

const mockSwitchProject = vi.fn()
let mockProjects = []
let mockProjectSlug = 'tablaco'

vi.mock('../contexts/ManifestProvider', () => ({
  useManifest: () => ({
    projects: mockProjects,
    projectSlug: mockProjectSlug,
    switchProject: mockSwitchProject,
  }),
}))

import ProjectSelector from './ProjectSelector'

describe('ProjectSelector', () => {
  it('returns null when no projects', () => {
    mockProjects = []
    const { container } = render(<ProjectSelector />)
    expect(container.firstChild).toBeNull()
  })

  it('returns null when single project', () => {
    mockProjects = [{ slug: 'tablaco', name: 'Tablaco' }]
    const { container } = render(<ProjectSelector />)
    expect(container.firstChild).toBeNull()
  })

  it('renders select with projects', () => {
    mockProjects = [
      { slug: 'tablaco', name: 'Tablaco' },
      { slug: 'demo', name: 'Demo' },
    ]
    render(<ProjectSelector />)
    expect(screen.getByLabelText('Select project')).toBeInTheDocument()
    expect(screen.getByText('Tablaco')).toBeInTheDocument()
    expect(screen.getByText('Demo')).toBeInTheDocument()
  })

  it('calls switchProject on change', () => {
    mockProjects = [
      { slug: 'tablaco', name: 'Tablaco' },
      { slug: 'demo', name: 'Demo' },
    ]
    render(<ProjectSelector />)
    fireEvent.change(screen.getByLabelText('Select project'), { target: { value: 'demo' } })
    expect(mockSwitchProject).toHaveBeenCalledWith('demo')
  })

  it('sets hash for github import option', () => {
    mockProjects = [
      { slug: 'tablaco', name: 'Tablaco' },
      { slug: 'demo', name: 'Demo' },
    ]
    render(<ProjectSelector />)
    fireEvent.change(screen.getByLabelText('Select project'), { target: { value: '__github_import__' } })
    expect(window.location.hash).toBe('#/projects')
  })
})
