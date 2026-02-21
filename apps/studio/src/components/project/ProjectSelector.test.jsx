import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

const mockSwitchProject = vi.fn()
let mockProjects = []
let mockProjectSlug = 'gridfinity'

vi.mock('../../contexts/project/ManifestProvider', () => ({
  useManifest: () => ({
    projects: mockProjects,
    projectSlug: mockProjectSlug,
    switchProject: mockSwitchProject,
  }),
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate
}))

import ProjectSelector from './ProjectSelector'

describe('ProjectSelector', () => {
  it('returns null when no projects', () => {
    mockProjects = []
    const { container } = render(<ProjectSelector />)
    expect(container.firstChild).toBeNull()
  })

  it('returns null when single project', () => {
    mockProjects = [{ slug: 'gridfinity', name: 'Gridfinity Extended' }]
    const { container } = render(<ProjectSelector />)
    expect(container.firstChild).toBeNull()
  })

  it('renders select with projects', () => {
    mockProjects = [
      { slug: 'gridfinity', name: 'Gridfinity Extended' },
      { slug: 'demo', name: 'Demo' },
    ]
    render(<ProjectSelector />)
    expect(screen.getByLabelText('Select project')).toBeInTheDocument()
    expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
    expect(screen.getByText('Demo')).toBeInTheDocument()
  })

  it('calls switchProject on change', () => {
    mockProjects = [
      { slug: 'gridfinity', name: 'Gridfinity Extended' },
      { slug: 'demo', name: 'Demo' },
    ]
    render(<ProjectSelector />)
    fireEvent.change(screen.getByLabelText('Select project'), { target: { value: 'demo' } })
    expect(mockSwitchProject).toHaveBeenCalledWith('demo')
  })

  it('navigates to projects for github import option', () => {
    mockProjects = [
      { slug: 'gridfinity', name: 'Gridfinity Extended' },
      { slug: 'demo', name: 'Demo' },
    ]
    render(<ProjectSelector />)
    fireEvent.change(screen.getByLabelText('Select project'), { target: { value: '__github_import__' } })
    expect(mockNavigate).toHaveBeenCalledWith('/projects')
  })
})
