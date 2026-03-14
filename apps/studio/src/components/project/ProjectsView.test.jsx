import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent, within } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import ProjectsView from './ProjectsView'
import { renderWithProviders } from '../../test/render-with-providers'
import fallbackManifest from '../../config/fallback-manifest.json'

expect.extend(toHaveNoViolations)

// Mock Viewer (imported transitively by ManifestProvider context)
vi.mock('./Viewer', () => ({
  // eslint-disable-next-line no-unused-vars
  default: React.forwardRef(function MockViewer(props, ref) { return <div data-testid="viewer-mock" /> }),
}))

// Mock lazy-loaded components so Suspense resolves immediately
vi.mock('../ai/GitHubImportWizard', () => ({
  default: function MockGitHubImportWizard({ onClose, onImported }) {
    return (
      <div data-testid="github-import-wizard">
        <button data-testid="wizard-close" onClick={onClose}>Close</button>
        <button data-testid="wizard-imported" onClick={onImported}>Imported</button>
      </div>
    )
  },
}))

vi.mock('./ProjectCarousel3D', () => ({
  default: function MockProjectCarousel3D({ projects }) {
    return <div data-testid="project-carousel-3d">{projects.length} projects</div>
  },
}))

const mockProjects = [
  {
    slug: 'gridfinity',
    name: 'Gridfinity Extended',
    version: '1.0.0',
    description: 'Modular storage bins',
    mode_count: 2,
    parameter_count: 6,
    scad_file_count: 3,
    has_manifest: true,
    has_exports: true,
    modified_at: 1700100000,
    tags: ['storage', 'gridfinity'],
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
    tags: ['storage'],
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
    tags: ['box'],
    difficulty: 'beginner',
    is_hyperobject: true,
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
    tags: ['keyboard'],
    difficulty: 'advanced',
    is_demo: true,
  },
]

beforeEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
})

const mockFetchSuccess = (projects = mockProjects) => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
    if (url.toString().includes('/manifest')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(fallbackManifest),
      })
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(projects),
    })
  })
}

/** Helper: wait for project cards to render */
const waitForProjects = async () => {
  await waitFor(() => {
    expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
  })
}

describe('ProjectsView', () => {
  it('renders loading state', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => { })) // never resolves
    renderWithProviders(<ProjectsView />)
    expect(screen.getByText('Loading projects\u2026')).toBeInTheDocument()
  })

  it('renders project cards on successful fetch', async () => {
    mockFetchSuccess()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()
    expect(screen.getAllByText('Gridfinity Extended')).toHaveLength(1)
    expect(screen.getAllByText('Portacosas')).toHaveLength(1)
  })

  it('renders error message on fetch failure with retry and demo buttons', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument()
    })
    expect(screen.getByText('Retry')).toBeInTheDocument()
    expect(screen.getByText('Open Demo Project')).toBeInTheDocument()
  })

  it('renders error on HTTP error status', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url.toString().includes('/manifest')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(fallbackManifest) })
      }
      return Promise.resolve({ ok: false, status: 500 })
    })
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText(/HTTP 500/)).toBeInTheDocument()
    })
  })

  it('retry button re-fetches projects on click', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock.mockRejectedValueOnce(new Error('Network error'))
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument()
    })

    // Mock a successful retry
    fetchMock.mockImplementation((url) => {
      if (url.toString().includes('/manifest')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(fallbackManifest) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProjects) })
    })

    fireEvent.click(screen.getByText('Retry'))

    await waitFor(() => {
      expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
    })
  })

  it('demo button renders and is clickable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument()
    })

    const demoBtn = screen.getByText('Open Demo Project')
    expect(demoBtn).toBeInTheDocument()
    expect(demoBtn.tagName).toBe('BUTTON')
    // Click should not throw — it navigates to /project/{fallback slug}
    expect(() => fireEvent.click(demoBtn)).not.toThrow()
  })

  it('renders empty state with CTA link', async () => {
    mockFetchSuccess([])
    renderWithProviders(<ProjectsView />, { tier: 'pro' })
    await waitFor(() => {
      expect(screen.getByText('No projects found.')).toBeInTheDocument()
    })
    const link = screen.getByText('Create your first project \u2192')
    expect(link).toBeInTheDocument()
    expect(link.tagName).toBe('BUTTON')
  })

  it('card links point to /project/{slug}', async () => {
    mockFetchSuccess()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()
    const links = screen.getAllByRole('link')
    const projectLinks = links.filter(l => l.getAttribute('href')?.startsWith('/project/'))
    expect(projectLinks.some(l => l.getAttribute('href') === '/project/gridfinity')).toBe(true)
    expect(projectLinks.some(l => l.getAttribute('href') === '/project/portacosas')).toBe(true)
  })

  it('renders translated strings in Spanish', async () => {
    mockFetchSuccess()
    renderWithProviders(<ProjectsView />, { language: 'es' })
    await waitFor(() => {
      expect(screen.getByText('Proyectos')).toBeInTheDocument()
    })
  })

  it('has no a11y violations', { timeout: 15000 }, async () => {
    mockFetchSuccess()
    const { container } = renderWithProviders(<ProjectsView />)
    await waitForProjects()
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  it('renders analytics stats badges when present', async () => {
    const projectsWithStats = mockProjects.map((p, i) =>
      i === 0 ? { ...p, stats: { renders: 42, exports: 7 } } : p
    )
    mockFetchSuccess(projectsWithStats)
    renderWithProviders(<ProjectsView />)
    await waitForProjects()
    expect(screen.getByTestId('stats-renders')).toHaveTextContent('42 renders')
    expect(screen.getByTestId('stats-exports')).toHaveTextContent('7 exports')
  })

  it('renders Manifest and Exports badges', async () => {
    mockFetchSuccess()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()
    expect(screen.getAllByTestId('manifest-badge')).toHaveLength(4)
    expect(screen.getAllByTestId('exports-badge')).toHaveLength(2)
  })

  it('renders render speed badges correctly', async () => {
    const projectsWithSpeed = [
      { ...mockProjects[0], estimate_constants: { base_time: 1, per_part: 0.5 } },
      { ...mockProjects[1], estimate_constants: { base_time: 5, per_part: 1 } },
      { ...mockProjects[2], estimate_constants: { base_time: 10, per_part: 2 } },
    ]
    mockFetchSuccess(projectsWithSpeed)
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText('Fast Render')).toBeInTheDocument()
    })
    expect(screen.getByText('Medium Render')).toBeInTheDocument()
    expect(screen.getByText('Slow Render')).toBeInTheDocument()
  })

  // --- Search filtering ---

  describe('search filtering', () => {
    it('filters by project name', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      const searchInput = screen.getByPlaceholderText(/Search projects/i)
      fireEvent.change(searchInput, { target: { value: 'gridfinity' } })

      expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
      expect(screen.queryByText('Portacosas')).not.toBeInTheDocument()
      expect(screen.queryByText('Ultimate Box')).not.toBeInTheDocument()
    })

    it('filters by description text', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      const searchInput = screen.getByPlaceholderText(/Search projects/i)
      fireEvent.change(searchInput, { target: { value: 'storage bins' } })

      expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
      expect(screen.queryByText('KeyV2')).not.toBeInTheDocument()
    })

    it('filters by slug', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      const searchInput = screen.getByPlaceholderText(/Search projects/i)
      fireEvent.change(searchInput, { target: { value: 'keyv2' } })

      expect(screen.getByText('KeyV2')).toBeInTheDocument()
      expect(screen.queryByText('Gridfinity Extended')).not.toBeInTheDocument()
    })

    it('filters by tag text', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      const searchInput = screen.getByPlaceholderText(/Search projects/i)
      fireEvent.change(searchInput, { target: { value: 'keyboard' } })

      expect(screen.getByText('KeyV2')).toBeInTheDocument()
      expect(screen.queryByText('Gridfinity Extended')).not.toBeInTheDocument()
    })

    it('is case insensitive', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      const searchInput = screen.getByPlaceholderText(/Search projects/i)
      fireEvent.change(searchInput, { target: { value: 'ULTIMATE BOX' } })

      expect(screen.getByText('Ultimate Box')).toBeInTheDocument()
      expect(screen.queryByText('Gridfinity Extended')).not.toBeInTheDocument()
    })

    it('shows no results state when search matches nothing', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      const searchInput = screen.getByPlaceholderText(/Search projects/i)
      fireEvent.change(searchInput, { target: { value: 'zzzznonexistent' } })

      expect(screen.getByText('No projects match your search.')).toBeInTheDocument()
      expect(screen.queryByText('Gridfinity Extended')).not.toBeInTheDocument()
    })

    it('restores all projects when search is cleared', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      const searchInput = screen.getByPlaceholderText(/Search projects/i)
      fireEvent.change(searchInput, { target: { value: 'gridfinity' } })
      expect(screen.queryByText('Portacosas')).not.toBeInTheDocument()

      fireEvent.change(searchInput, { target: { value: '' } })
      expect(screen.getByText('Portacosas')).toBeInTheDocument()
      expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
    })
  })

  // --- Tag filtering ---

  describe('tag filtering', () => {
    it('renders tag buttons for all unique tags', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      // Tags from mockProjects: storage, gridfinity, box, keyboard
      expect(screen.getByRole('button', { name: 'storage' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'gridfinity' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'box' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'keyboard' })).toBeInTheDocument()
    })

    it('filters projects when a tag button is clicked', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      fireEvent.click(screen.getByRole('button', { name: 'keyboard' }))

      expect(screen.getByText('KeyV2')).toBeInTheDocument()
      expect(screen.queryByText('Gridfinity Extended')).not.toBeInTheDocument()
      expect(screen.queryByText('Portacosas')).not.toBeInTheDocument()
    })

    it('deselects tag when clicked again (toggle)', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      const tagBtn = screen.getByRole('button', { name: 'keyboard' })

      // Click to activate
      fireEvent.click(tagBtn)
      expect(screen.queryByText('Gridfinity Extended')).not.toBeInTheDocument()

      // Click again to deactivate
      fireEvent.click(tagBtn)
      expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
      expect(screen.getByText('KeyV2')).toBeInTheDocument()
    })

    it('shows multiple projects sharing the same tag', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      // Both gridfinity and portacosas have the 'storage' tag
      fireEvent.click(screen.getByRole('button', { name: 'storage' }))

      expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
      expect(screen.getByText('Portacosas')).toBeInTheDocument()
      expect(screen.queryByText('Ultimate Box')).not.toBeInTheDocument()
    })

    it('does not show tag buttons when no projects have tags', async () => {
      const noTagProjects = mockProjects.map(p => ({ ...p, tags: undefined }))
      mockFetchSuccess(noTagProjects)
      renderWithProviders(<ProjectsView />)
      await waitFor(() => {
        expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
      })

      // No tag buttons should exist
      expect(screen.queryByRole('button', { name: 'storage' })).not.toBeInTheDocument()
    })
  })

  // --- View mode ---

  describe('view mode', () => {
    it('defaults to grid view with project cards', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      // Grid view renders Link cards (role=link)
      const projectLinks = screen.getAllByRole('link').filter(l =>
        l.getAttribute('href')?.startsWith('/project/')
      )
      expect(projectLinks.length).toBe(4)
      // Carousel not rendered
      expect(screen.queryByTestId('project-carousel-3d')).not.toBeInTheDocument()
    })

    it('switches to list view', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      const listToggle = screen.getByRole('radio', { name: /List view/i })
      fireEvent.click(listToggle)

      await waitFor(() => {
        expect(screen.getAllByTestId('project-row').length).toBe(4)
      })
    })

    it('switches to 3D carousel view', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      const carouselToggle = screen.getByRole('radio', { name: /3D Carousel view/i })
      fireEvent.click(carouselToggle)

      await waitFor(() => {
        expect(screen.getByTestId('project-carousel-3d')).toBeInTheDocument()
      })
    })
  })

  // --- Difficulty badge ---

  describe('difficulty badges', () => {
    it('renders difficulty badge when present', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      expect(screen.getByText('beginner')).toBeInTheDocument()
      expect(screen.getByText('advanced')).toBeInTheDocument()
    })
  })

  // --- Import wizard ---

  describe('import wizard', () => {
    it('opens import wizard and closes on wizard close callback', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />, { tier: 'pro' })
      await waitForProjects()

      fireEvent.click(screen.getByText('Import'))

      await waitFor(() => {
        expect(screen.getByTestId('github-import-wizard')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByTestId('wizard-close'))

      await waitFor(() => {
        expect(screen.queryByTestId('github-import-wizard')).not.toBeInTheDocument()
      })
    })

    it('refreshes project list when import succeeds', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />, { tier: 'pro' })
      await waitForProjects()

      fireEvent.click(screen.getByText('Import'))

      await waitFor(() => {
        expect(screen.getByTestId('github-import-wizard')).toBeInTheDocument()
      })

      // Click the imported button which triggers onImported callback
      fireEvent.click(screen.getByTestId('wizard-imported'))

      // The wizard should close and a refresh fetch should be made
      await waitFor(() => {
        expect(screen.queryByTestId('github-import-wizard')).not.toBeInTheDocument()
      })
    })

    it('opens import wizard from empty state CTA', async () => {
      mockFetchSuccess([])
      renderWithProviders(<ProjectsView />, { tier: 'pro' })
      await waitFor(() => {
        expect(screen.getByText('No projects found.')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('Create your first project \u2192'))

      await waitFor(() => {
        expect(screen.getByTestId('github-import-wizard')).toBeInTheDocument()
      })
    })
  })

  // --- Localized description ---

  describe('localized description', () => {
    it('handles object-style description with language key', async () => {
      const projectsWithI18n = [
        {
          ...mockProjects[0],
          description: { en: 'English bins', es: 'Contenedores' },
        },
      ]
      mockFetchSuccess(projectsWithI18n)
      renderWithProviders(<ProjectsView />, { language: 'es' })
      await waitFor(() => {
        expect(screen.getByText('Contenedores')).toBeInTheDocument()
      })
    })
  })

  // --- Project card details ---

  describe('project card content', () => {
    it('renders mode and parameter counts with correct pluralization', async () => {
      const singleModeProject = [
        { ...mockProjects[0], mode_count: 1, parameter_count: 1 },
      ]
      mockFetchSuccess(singleModeProject)
      renderWithProviders(<ProjectsView />)
      await waitFor(() => {
        expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
      })

      expect(screen.getByText('1 mode')).toBeInTheDocument()
      expect(screen.getByText('1 param')).toBeInTheDocument()
    })

    it('renders thumbnail image when present', async () => {
      const projectsWithThumb = [
        { ...mockProjects[0], thumbnail: '/thumb/gridfinity.png' },
      ]
      mockFetchSuccess(projectsWithThumb)
      renderWithProviders(<ProjectsView />)
      await waitFor(() => {
        expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
      })

      const img = screen.getByAltText('Gridfinity Extended')
      expect(img).toBeInTheDocument()
      expect(img).toHaveAttribute('src', '/thumb/gridfinity.png')
    })

    it('renders tag chips on project cards', async () => {
      mockFetchSuccess()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      // The gridfinity card should show its tags
      const gridfinityLink = screen.getAllByRole('link').find(l =>
        l.getAttribute('href') === '/project/gridfinity'
      )
      expect(within(gridfinityLink).getByText('storage')).toBeInTheDocument()
      expect(within(gridfinityLink).getByText('gridfinity')).toBeInTheDocument()
    })
  })
})
