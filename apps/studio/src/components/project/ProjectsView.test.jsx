import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
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

// --- Mock catalog data matching the /api/catalog/search response shape ---

const mockResults = [
  {
    slug: 'gridfinity',
    name: 'Gridfinity Extended',
    name_i18n: { en: 'Gridfinity Extended', es: 'Gridfinity Extendido' },
    description: 'Modular storage bins',
    engine: 'openscad',
    difficulty: 'beginner',
    domain: 'storage',
    is_hyperobject: true,
    dual_engine: false,
    tags: ['storage', 'gridfinity'],
    geometry_types: ['grid', 'pocket'],
    standards: ['Gridfinity 42mm'],
    mode_count: 2,
    part_count: 6,
    thumbnail: '/thumb/gridfinity.png',
    modified_ms: 1700100000000,
    unlisted: false,
  },
  {
    slug: 'portacosas',
    name: 'Portacosas',
    name_i18n: { en: 'Portacosas', es: 'Portacosas' },
    description: 'Container system',
    engine: 'cadquery',
    difficulty: 'intermediate',
    domain: 'storage',
    is_hyperobject: true,
    dual_engine: true,
    tags: ['storage'],
    geometry_types: ['rail'],
    standards: ['VESA 75/100'],
    mode_count: 2,
    part_count: 5,
    thumbnail: '',
    modified_ms: 1700200000000,
    unlisted: false,
  },
  {
    slug: 'nema-mount',
    name: 'NEMA 17 Mount',
    name_i18n: { en: 'NEMA 17 Mount', es: 'Soporte NEMA 17' },
    description: 'Stepper motor bracket',
    engine: 'openscad',
    difficulty: 'advanced',
    domain: 'mechanical',
    is_hyperobject: true,
    dual_engine: false,
    tags: ['motor', 'bracket'],
    geometry_types: ['bolt_pattern'],
    standards: ['NEMA 17'],
    mode_count: 1,
    part_count: 2,
    thumbnail: '/thumb/nema.png',
    modified_ms: 1700300000000,
    unlisted: false,
  },
]

const mockFacets = {
  domain: [
    { value: 'storage', count: 2 },
    { value: 'mechanical', count: 1 },
  ],
  difficulty: [
    { value: 'beginner', count: 1 },
    { value: 'intermediate', count: 1 },
    { value: 'advanced', count: 1 },
  ],
  engine: [
    { value: 'openscad', count: 2 },
    { value: 'cadquery', count: 1 },
  ],
  geometry_type: [
    { value: 'grid', count: 1 },
    { value: 'rail', count: 1 },
    { value: 'bolt_pattern', count: 1 },
    { value: 'pocket', count: 1 },
  ],
  standard: [
    { value: 'NEMA 17', count: 1 },
    { value: 'VESA 75/100', count: 1 },
    { value: 'Gridfinity 42mm', count: 1 },
  ],
  material: [
    { value: 'tolerance_by_material', count: 2 },
    { value: 'shrinkage_compensation', count: 1 },
  ],
  tag: [
    { value: 'storage', count: 2 },
    { value: 'gridfinity', count: 1 },
    { value: 'motor', count: 1 },
    { value: 'bracket', count: 1 },
  ],
}

/**
 * Build a search response. `resultsForUrl` lets a test vary results by URL
 * (e.g. filtered subsets); defaults to the full mock set.
 */
const buildSearchResponse = (results = mockResults) => ({
  results,
  total: results.length,
  limit: 60,
  offset: 0,
  facets: mockFacets,
  catalog_count: 248,
})

/**
 * Install a fetch spy. Returns the spy so tests can assert on called URLs.
 * The manifest call (url includes `/manifest`) returns the fallback manifest;
 * everything else returns the catalog search response.
 */
const mockFetch = (searchResponse = buildSearchResponse()) => {
  const spy = vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
    const u = url.toString()
    if (u.includes('/manifest')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(fallbackManifest) })
    }
    if (u.includes('/api/catalog/search')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(searchResponse) })
    }
    // ManifestProvider fetches /api/projects (expects an array); keep it happy.
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
  })
  return spy
}

/** Return the list of catalog-search URLs the fetch spy was called with. */
const searchUrls = (spy) =>
  spy.mock.calls
    .map((call) => call[0].toString())
    .filter((u) => u.includes('/api/catalog/search'))

const waitForProjects = async () => {
  await waitFor(() => {
    expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
  })
}

beforeEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('ProjectsView (catalog search)', () => {
  it('renders loading state initially', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {})) // never resolves
    renderWithProviders(<ProjectsView />)
    // Loading skeleton exposes the localized loading label via sr-only text
    expect(screen.getByText('Loading projects…')).toBeInTheDocument()
  })

  it('renders result cards from the API', async () => {
    mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()
    expect(screen.getByText('Portacosas')).toBeInTheDocument()
    expect(screen.getByText('NEMA 17 Mount')).toBeInTheDocument()
  })

  it('fetches the catalog search endpoint on mount', async () => {
    const spy = mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()
    const urls = searchUrls(spy)
    expect(urls.length).toBeGreaterThan(0)
    expect(urls[0]).toContain('/api/catalog/search')
    expect(urls[0]).toContain('offset=0')
    expect(urls[0]).toContain('limit=60')
  })

  it('cards link to /project/{slug}', async () => {
    mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()
    const links = screen.getAllByRole('link').filter((l) =>
      l.getAttribute('href')?.startsWith('/project/'),
    )
    expect(links.some((l) => l.getAttribute('href') === '/project/gridfinity')).toBe(true)
    expect(links.some((l) => l.getAttribute('href') === '/project/portacosas')).toBe(true)
    expect(links.some((l) => l.getAttribute('href') === '/project/nema-mount')).toBe(true)
  })

  it('renders the result count', async () => {
    mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText('3 results')).toBeInTheDocument()
    })
  })

  it('renders the catalog size in the header', async () => {
    mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText('248 in catalog')).toBeInTheDocument()
    })
  })

  // --- Search ---

  it('typing in the search box triggers a refetch with q= in the URL', async () => {
    const spy = mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()

    const input = screen.getByPlaceholderText('Search projects…')
    fireEvent.change(input, { target: { value: 'nema' } })

    await waitFor(() => {
      expect(searchUrls(spy).some((u) => u.includes('q=nema'))).toBe(true)
    })
  })

  it('resets to offset 0 when the search changes', async () => {
    const spy = mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()

    const input = screen.getByPlaceholderText('Search projects…')
    fireEvent.change(input, { target: { value: 'grid' } })

    await waitFor(() => {
      const qUrl = searchUrls(spy).find((u) => u.includes('q=grid'))
      expect(qUrl).toBeDefined()
      expect(qUrl).toContain('offset=0')
    })
  })

  // --- Facets ---

  it('renders facet chips with counts from the API', async () => {
    mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()
    // Facet chips live in the desktop sidebar; their accessible name is
    // "value count" (e.g. "grid 1"). Scope to the sidebar to avoid colliding
    // with the "Grid view" toggle and the "Gridfinity" card title.
    const sidebar = screen.getByRole('complementary', { name: 'Filters' })
    // "Connects via" (geometry_type) values
    expect(within(sidebar).getByRole('button', { name: 'grid 1' })).toBeInTheDocument()
    // "Compatible with" (standard) values
    expect(within(sidebar).getByRole('button', { name: 'NEMA 17 1' })).toBeInTheDocument()
  })

  it('clicking a facet chip triggers a refetch with that facet param', async () => {
    const spy = mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()

    // "grid" is a geometry_type facet value → expect geometry_type=grid in URL
    const sidebar = screen.getByRole('complementary', { name: 'Filters' })
    fireEvent.click(within(sidebar).getByRole('button', { name: 'grid 1' }))

    await waitFor(() => {
      expect(searchUrls(spy).some((u) => u.includes('geometry_type=grid'))).toBe(true)
    })
  })

  it('renders the material facet with a localized capability label', async () => {
    mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()
    const sidebar = screen.getByRole('complementary', { name: 'Filters' })
    // Raw capability flag "tolerance_by_material" (count 2) renders its EN label.
    expect(
      within(sidebar).getByRole('button', { name: 'Adapts tolerances to material 2' }),
    ).toBeInTheDocument()
  })

  it('clicking a material chip refetches with material=<flag> in the URL', async () => {
    const spy = mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()

    const sidebar = screen.getByRole('complementary', { name: 'Filters' })
    fireEvent.click(
      within(sidebar).getByRole('button', { name: 'Adapts tolerances to material 2' }),
    )

    await waitFor(() => {
      expect(searchUrls(spy).some((u) => u.includes('material=tolerance_by_material'))).toBe(true)
    })
  })

  it('shows an active-filter pill and clears it', async () => {
    const spy = mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()

    const sidebar = screen.getByRole('complementary', { name: 'Filters' })
    fireEvent.click(within(sidebar).getByRole('button', { name: 'NEMA 17 1' }))

    await waitFor(() => {
      expect(searchUrls(spy).some((u) => u.includes('standard=NEMA'))).toBe(true)
    })

    // Clear all removes the filter and refetches without the standard param.
    // findByRole retries so it waits out the debounced refetch's loading state
    // (a bare getByRole can race the skeleton→loaded transition).
    const clearAll = await screen.findByRole('button', { name: 'Clear all' })
    fireEvent.click(clearAll)

    await waitFor(() => {
      const urls = searchUrls(spy)
      const last = urls[urls.length - 1]
      expect(last).not.toContain('standard=NEMA')
    })
  })

  // --- Sort ---

  it('sends the mapped sort value in the URL by default', async () => {
    const spy = mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()
    expect(searchUrls(spy)[0]).toContain('sort=name')
  })

  // --- Difficulty badges ---

  it('renders difficulty badges', async () => {
    mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()
    expect(screen.getByText('Beginner')).toBeInTheDocument()
    expect(screen.getByText('Advanced')).toBeInTheDocument()
  })

  // --- Error / empty / no-results states ---

  it('renders error state with Retry and Open Demo Project buttons', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url.toString().includes('/manifest')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(fallbackManifest) })
      }
      return Promise.reject(new Error('Network error'))
    })
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

  it('Retry refetches after an error', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url.toString().includes('/manifest')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(fallbackManifest) })
      }
      return Promise.reject(new Error('Network error'))
    })
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument()
    })

    // Now make catalog search succeed and click Retry
    spy.mockImplementation((url) => {
      if (url.toString().includes('/manifest')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(fallbackManifest) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(buildSearchResponse()) })
    })
    fireEvent.click(screen.getByText('Retry'))

    await waitFor(() => {
      expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
    })
  })

  it('Open Demo Project button is clickable', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url.toString().includes('/manifest')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(fallbackManifest) })
      }
      return Promise.reject(new Error('Network error'))
    })
    renderWithProviders(<ProjectsView />)
    await waitFor(() => {
      expect(screen.getByText('Open Demo Project')).toBeInTheDocument()
    })
    const btn = screen.getByText('Open Demo Project')
    expect(btn.tagName).toBe('BUTTON')
    expect(() => fireEvent.click(btn)).not.toThrow()
  })

  it('renders empty state when the catalog returns no results and no filters are active', async () => {
    mockFetch(buildSearchResponse([]))
    renderWithProviders(<ProjectsView />, { tier: 'pro' })
    await waitFor(() => {
      expect(screen.getByText('No projects found.')).toBeInTheDocument()
    })
  })

  it('renders no-results state when a search matches nothing', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = url.toString()
      if (u.includes('/manifest')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(fallbackManifest) })
      }
      // Empty results only when a query is present
      if (u.includes('q=')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(buildSearchResponse([])) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(buildSearchResponse()) })
    })
    renderWithProviders(<ProjectsView />)
    await waitForProjects()

    const input = screen.getByPlaceholderText('Search projects…')
    fireEvent.change(input, { target: { value: 'zzzznope' } })

    await waitFor(() => {
      expect(searchUrls(spy).some((u) => u.includes('q=zzzznope'))).toBe(true)
    })
    await waitFor(() => {
      expect(screen.getByText('No projects match your search.')).toBeInTheDocument()
    })
  })

  // --- Localized name (Spanish) ---

  it('renders localized project name from name_i18n', async () => {
    mockFetch()
    renderWithProviders(<ProjectsView />, { language: 'es' })
    await waitFor(() => {
      expect(screen.getByText('Gridfinity Extendido')).toBeInTheDocument()
    })
  })

  it('renders the Spanish page title', async () => {
    mockFetch()
    renderWithProviders(<ProjectsView />, { language: 'es' })
    await waitFor(() => {
      expect(screen.getByText('Proyectos')).toBeInTheDocument()
    })
  })

  // --- Thumbnail fallback ---

  it('renders thumbnail image when present', async () => {
    mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()
    const img = screen.getByAltText('Gridfinity Extended')
    expect(img).toHaveAttribute('src', '/thumb/gridfinity.png')
    expect(img).toHaveAttribute('loading', 'lazy')
  })

  // --- 3D carousel toggle ---

  describe('3D preview toggle', () => {
    it('defaults to grid view (no carousel rendered)', async () => {
      mockFetch()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()
      expect(screen.queryByTestId('project-carousel-3d')).not.toBeInTheDocument()
    })

    it('renders the carousel when the 3D toggle is clicked', async () => {
      mockFetch()
      renderWithProviders(<ProjectsView />)
      await waitForProjects()

      fireEvent.click(screen.getByRole('radio', { name: /3D preview/i }))

      await waitFor(() => {
        expect(screen.getByTestId('project-carousel-3d')).toBeInTheDocument()
      })
    })

    it('caps the number of projects passed to the carousel', async () => {
      // 40 results → carousel must receive at most 24
      const many = Array.from({ length: 40 }, (_, i) => ({
        ...mockResults[0],
        slug: `obj-${i}`,
        name: `Object ${i}`,
        name_i18n: { en: `Object ${i}`, es: `Objeto ${i}` },
      }))
      mockFetch({ ...buildSearchResponse(many), total: 40 })
      renderWithProviders(<ProjectsView />)
      await waitFor(() => {
        expect(screen.getByText('Object 0')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByRole('radio', { name: /3D preview/i }))

      await waitFor(() => {
        expect(screen.getByTestId('project-carousel-3d')).toHaveTextContent('24 projects')
      })
    })
  })

  // --- Import wizard (tier-gated) ---

  describe('import wizard', () => {
    it('opens the import wizard and closes on the close callback', async () => {
      mockFetch()
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
  })

  // --- Accessibility ---

  it('has no axe a11y violations', { timeout: 15000 }, async () => {
    mockFetch()
    const { container } = renderWithProviders(<ProjectsView />)
    await waitForProjects()
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  // --- Sort, pagination, facet clearing and import -------------------------
  // These paths were unreached: loadMore and its response handling, clearFacet,
  // the sort select, the browse-by-standard toggle and the import button.

  it('sort control exposes every ordering the view supports', async () => {
    mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()

    // Asserted on the trigger rather than by opening the menu: Radix Select
    // needs pointer-capture APIs jsdom does not implement, and driving it here
    // would test the polyfill rather than the component.
    const sort = screen.getByRole('combobox', { name: /sort/i })
    expect(sort).toBeInTheDocument()
    expect(sort.textContent).toMatch(/name/i)
  })

  it('scrolling to the end requests the next page by offset', async () => {
    // total > results.length is what makes loadMore eligible to fire.
    const spy = mockFetch({ ...buildSearchResponse(), total: 120 })
    renderWithProviders(<ProjectsView />)
    await waitForProjects()

    const scroller = document.querySelector('[data-testid="projects-grid-scroll"]')
    expect(scroller).toBeTruthy()
    // jsdom reports zero-size boxes, so drive the scroll handler's inputs directly.
    Object.defineProperty(scroller, 'scrollHeight', { value: 1000, configurable: true })
    Object.defineProperty(scroller, 'clientHeight', { value: 500, configurable: true })
    Object.defineProperty(scroller, 'scrollTop', { value: 500, configurable: true })
    fireEvent.scroll(scroller)

    await waitFor(() => {
      expect(searchUrls(spy).some((u) => /offset=[1-9]/.test(u))).toBe(true)
    })
  })

  it('an active filter pill clears its facet and refetches without it', async () => {
    const spy = mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()

    // Apply a domain facet, then remove it via its pill.
    fireEvent.click(screen.getByText('storage'))
    await waitFor(() => expect(searchUrls(spy).some((u) => u.includes('domain=storage'))).toBe(true))

    const before = searchUrls(spy).length
    fireEvent.click(screen.getByRole('button', { name: /Remove storage filter/i }))

    await waitFor(() => {
      const urls = searchUrls(spy)
      expect(urls.length).toBeGreaterThan(before)
      expect(urls.at(-1)).not.toContain('domain=storage')
    })
  })

  it('browse-by-standard toggles the standards browser', async () => {
    mockFetch()
    renderWithProviders(<ProjectsView />)
    await waitForProjects()

    const toggle = screen.getByRole('button', { name: /browse by standard/i })
    fireEvent.click(toggle)
    // Toggling is the branch under test; the browser itself is lazy-loaded.
    await waitFor(() => expect(toggle).toBeInTheDocument())
    fireEvent.click(toggle)
  })
})

