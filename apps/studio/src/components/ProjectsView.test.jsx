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
    slug: 'tablaco',
    name: 'Tablaco Studio',
    version: '1.0.0',
    description: 'Interlocking cube system',
    mode_count: 3,
    parameter_count: 8,
    scad_file_count: 4,
    has_manifest: true,
    has_exports: true,
    modified_at: 1700000000,
  },
  {
    slug: 'gridfinity',
    name: 'Gridfinity',
    version: '1.0.0',
    description: 'Modular storage bins',
    mode_count: 2,
    parameter_count: 6,
    scad_file_count: 3,
    has_manifest: true,
    has_exports: true,
    modified_at: 1700100000,
  },
  {
    slug: 'portacosas',
    name: 'Portacosas',
    version: '1.0.0',
    description: 'Container system',
    mode_count: 2,
    parameter_count: 5,
    scad_file_count: 2,
    has_manifest: true,
    has_exports: true,
    modified_at: 1700200000,
  },
  {
    slug: 'ultimate-box',
    name: 'Ultimate Box',
    version: '0.1.0',
    description: 'Parametric box maker',
    mode_count: 1,
    parameter_count: 10,
    scad_file_count: 2,
    has_manifest: true,
    has_exports: false,
    modified_at: 1700300000,
  },
  {
    slug: 'keyv2',
    name: 'KeyV2',
    version: '0.1.0',
    description: 'Parametric mechanical keycaps',
    mode_count: 1,
    parameter_count: 4,
    scad_file_count: 2,
    has_manifest: true,
    has_exports: false,
    modified_at: 1700400000,
  },
  {
    slug: 'multiboard',
    name: 'Multiboard',
    version: '0.1.0',
    description: 'Pegboard tiles',
    mode_count: 1,
    parameter_count: 3,
    scad_file_count: 2,
    has_manifest: true,
    has_exports: false,
    modified_at: 1700500000,
  },
  {
    slug: 'fasteners',
    name: 'Fasteners',
    version: '0.1.0',
    description: 'Nuts and bolts',
    mode_count: 2,
    parameter_count: 5,
    scad_file_count: 3,
    has_manifest: true,
    has_exports: false,
    modified_at: 1700600000,
  },
  {
    slug: 'gears',
    name: 'Gears',
    version: '0.1.0',
    description: 'Parametric gear generator',
    mode_count: 1,
    parameter_count: 6,
    scad_file_count: 2,
    has_manifest: true,
    has_exports: false,
    modified_at: 1700700000,
  },
  {
    slug: 'yapp-box',
    name: 'YAPP Box',
    version: '0.1.0',
    description: 'Yet Another Parametric Projectbox',
    mode_count: 2,
    parameter_count: 7,
    scad_file_count: 3,
    has_manifest: true,
    has_exports: false,
    modified_at: 1700800000,
  },
  {
    slug: 'stemfie',
    name: 'STEMFIE',
    version: '0.1.0',
    description: 'STEM construction kit',
    mode_count: 3,
    parameter_count: 4,
    scad_file_count: 4,
    has_manifest: true,
    has_exports: false,
    modified_at: 1700900000,
  },
  {
    slug: 'polydice',
    name: 'Polydice',
    version: '0.1.0',
    description: 'Parametric dice set',
    mode_count: 1,
    parameter_count: 3,
    scad_file_count: 2,
    has_manifest: true,
    has_exports: false,
    modified_at: 1701000000,
  },
  {
    slug: 'julia-vase',
    name: 'Julia Vase',
    version: '0.1.0',
    description: 'Fractal vase generator',
    mode_count: 1,
    parameter_count: 5,
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
      expect(screen.getByText('Tablaco Studio')).toBeInTheDocument()
    })
    expect(screen.getAllByText('v1.0.0')).toHaveLength(3)
    expect(screen.getAllByText('3 modes')).toHaveLength(2) // tablaco + stemfie
    expect(screen.getByText('8 params')).toBeInTheDocument()
    expect(screen.getByText('Gridfinity')).toBeInTheDocument()
    expect(screen.getByText('Julia Vase')).toBeInTheDocument()
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
      expect(screen.getByText('Tablaco Studio')).toBeInTheDocument()
    })
    const links = screen.getAllByRole('link')
    const projectLinks = links.filter(l => l.getAttribute('href')?.startsWith('#/'))
    expect(projectLinks.some(l => l.getAttribute('href') === '#/tablaco')).toBe(true)
    expect(projectLinks.some(l => l.getAttribute('href') === '#/julia-vase')).toBe(true)
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
    expect(screen.getAllByText('Exportaciones').length).toBeGreaterThan(0)
  })

  it('has no a11y violations', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockProjects),
    })
    const { container } = renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText('Tablaco Studio')).toBeInTheDocument()
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
      expect(screen.getByText('Tablaco Studio')).toBeInTheDocument()
    })
    // All 12 projects have manifest, 3 have exports (tablaco, gridfinity, portacosas)
    expect(screen.getAllByText('Manifest')).toHaveLength(12)
    expect(screen.getAllByText('Exports')).toHaveLength(3)
  })
})
