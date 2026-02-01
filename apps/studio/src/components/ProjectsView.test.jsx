import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import ProjectsView from './ProjectsView'
import { renderWithProviders } from '../test/render-with-providers'

expect.extend(toHaveNoViolations)

// Mock Viewer (imported transitively by ManifestProvider context)
vi.mock('./Viewer', () => ({
  // eslint-disable-next-line no-unused-vars
  default: React.forwardRef(function MockViewer(props, ref) { return <div data-testid="viewer-mock" /> }),
}))

const mockProjects = [
  {
    slug: 'test-project',
    name: 'Test Project',
    version: '1.0.0',
    description: 'A test project',
    mode_count: 2,
    parameter_count: 5,
    scad_file_count: 3,
    has_manifest: true,
    has_exports: true,
    modified_at: 1700000000,
  },
  {
    slug: 'another',
    name: 'Another',
    version: '0.1.0',
    description: '',
    mode_count: 1,
    parameter_count: 0,
    scad_file_count: 1,
    has_manifest: true,
    has_exports: false,
    modified_at: null,
  },
]

beforeEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
})

describe('ProjectsView', () => {
  it('renders loading state', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {})) // never resolves
    renderWithProviders(<ProjectsView />)
    expect(screen.getByText('Loading projects…')).toBeInTheDocument()
  })

  it('renders project cards on successful fetch', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockProjects),
    })
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText('Test Project')).toBeInTheDocument()
    })
    expect(screen.getByText('v1.0.0')).toBeInTheDocument()
    expect(screen.getByText('2 modes')).toBeInTheDocument()
    expect(screen.getByText('5 params')).toBeInTheDocument()
    expect(screen.getByText('3 .scad')).toBeInTheDocument()
    expect(screen.getByText('Another')).toBeInTheDocument()
    expect(screen.getByText('1 mode')).toBeInTheDocument()
    expect(screen.getByText('0 params')).toBeInTheDocument()
  })

  it('renders error message on fetch failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument()
    })
  })

  it('renders empty state with CTA link', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    })
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText('No projects found.')).toBeInTheDocument()
    })
    const link = screen.getByText('Create your first project →')
    expect(link).toHaveAttribute('href', '#/onboard')
  })

  it('card links point to #/{slug}', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockProjects),
    })
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText('Test Project')).toBeInTheDocument()
    })
    const links = screen.getAllByRole('link')
    const projectLinks = links.filter(l => l.getAttribute('href')?.startsWith('#/'))
    expect(projectLinks.some(l => l.getAttribute('href') === '#/test-project')).toBe(true)
    expect(projectLinks.some(l => l.getAttribute('href') === '#/another')).toBe(true)
  })

  it('renders translated strings in Spanish', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockProjects),
    })
    renderWithProviders(<ProjectsView />, { language: 'es' })
    await waitFor(() => {
      expect(screen.getByText('Proyectos')).toBeInTheDocument()
    })
    expect(screen.getAllByText('Manifiesto').length).toBeGreaterThan(0)
    expect(screen.getByText('Exportaciones')).toBeInTheDocument()
  })

  it('has no a11y violations', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockProjects),
    })
    const { container } = renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText('Test Project')).toBeInTheDocument()
    })
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  it('renders Manifest and Exports badges', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockProjects),
    })
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText('Test Project')).toBeInTheDocument()
    })
    // Both projects have manifest, only first has exports
    expect(screen.getAllByText('Manifest')).toHaveLength(2)
    expect(screen.getAllByText('Exports')).toHaveLength(1)
  })
})
