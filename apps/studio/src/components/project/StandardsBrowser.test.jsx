import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import StandardsBrowser, { familyLabel } from './StandardsBrowser'
import { renderWithProviders } from '../../test/render-with-providers'
import fallbackManifest from '../../config/fallback-manifest.json'

expect.extend(toHaveNoViolations)

// --- Mock families data matching the /api/catalog/families response shape ---

const mockFamilies = [
  { family: 'vesa', members: 3, slugs: ['vesa-mount', 'monitor-arm', 'wall-plate'] },
  { family: 'unc-1/4-20', members: 2, slugs: ['tripod-plate', 'camera-rig'] },
  { family: 'din-rail-35', members: 1, slugs: ['din-clip'] },
]

const buildFamiliesResponse = (families = mockFamilies) => ({
  families,
  count: families.length,
})

/**
 * Install a fetch spy that answers /api/catalog/families. Returns the spy so
 * tests can assert on called URLs. The provider chain (ManifestProvider) also
 * fetches /api/projects (expects an array) and a manifest (expects the manifest
 * shape); those are stubbed so the wrapping providers stay happy.
 */
const mockFetch = (response = buildFamiliesResponse()) =>
  vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
    const u = url.toString()
    if (u.includes('/api/catalog/families')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(response) })
    }
    if (u.includes('/manifest')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(fallbackManifest) })
    }
    // ManifestProvider fetches /api/projects (expects an array); keep it happy.
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
  })

const familyUrls = (spy) =>
  spy.mock.calls
    .map((call) => call[0].toString())
    .filter((u) => u.includes('/api/catalog/families'))

const waitForDirectory = async () => {
  await waitFor(() => {
    expect(screen.getByRole('button', { name: /VESA/ })).toBeInTheDocument()
  })
}

beforeEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('familyLabel (key → human label)', () => {
  it('maps curated internal keys to friendly labels', () => {
    expect(familyLabel('unc-1/4-20')).toBe('1/4-20 UNC')
    expect(familyLabel('din-rail-35')).toBe('DIN rail (35mm)')
    expect(familyLabel('vesa')).toBe('VESA')
    expect(familyLabel('nema-stepper')).toBe('NEMA stepper')
    expect(familyLabel('ght-hose')).toBe('GHT (garden hose)')
  })

  it('falls back to a title-cased key for unmapped families', () => {
    expect(familyLabel('some-new-standard')).toBe('Some New Standard')
    expect(familyLabel('foo_bar')).toBe('Foo Bar')
  })
})

describe('StandardsBrowser (family directory)', () => {
  it('renders the loading state initially', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {})) // never resolves
    renderWithProviders(<StandardsBrowser />)
    expect(screen.getByText('Loading standards…')).toBeInTheDocument()
  })

  it('fetches the families endpoint on mount', async () => {
    const spy = mockFetch()
    renderWithProviders(<StandardsBrowser />)
    await waitForDirectory()
    const urls = familyUrls(spy)
    expect(urls.length).toBeGreaterThan(0)
    expect(urls[0]).toContain('/api/catalog/families')
  })

  it('renders the family list with member counts, ranked as returned', async () => {
    mockFetch()
    renderWithProviders(<StandardsBrowser />)
    await waitForDirectory()

    // Curated labels are shown, not the raw keys.
    expect(screen.getByRole('button', { name: /VESA/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /1\/4-20 UNC/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /DIN rail \(35mm\)/ })).toBeInTheDocument()

    // Member counts appear on each row.
    expect(screen.getByText('3 objects')).toBeInTheDocument()
    expect(screen.getByText('2 objects')).toBeInTheDocument()
    expect(screen.getByText('1 objects')).toBeInTheDocument()

    // Directory subtitle reflects the number of families.
    expect(
      screen.getByText('3 interoperability families across the catalog'),
    ).toBeInTheDocument()
  })

  it('renders a directory from the families prop without fetching', async () => {
    const spy = mockFetch()
    renderWithProviders(<StandardsBrowser families={mockFamilies} />)
    await waitForDirectory()
    // Controlled mode: no families request is made.
    expect(familyUrls(spy)).toHaveLength(0)
  })

  it('members are hidden until a family is expanded', async () => {
    mockFetch()
    renderWithProviders(<StandardsBrowser />)
    await waitForDirectory()
    // Member cards are collapsed by default.
    expect(screen.queryByRole('link', { name: /Vesa Mount/ })).not.toBeInTheDocument()
  })

  it('clicking a family reveals its member objects as links to /project/<slug>', async () => {
    mockFetch()
    renderWithProviders(<StandardsBrowser />)
    await waitForDirectory()

    const vesaButton = screen.getByRole('button', { name: /VESA/ })
    expect(vesaButton).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(vesaButton)

    await waitFor(() => {
      expect(vesaButton).toHaveAttribute('aria-expanded', 'true')
    })

    // Member cards render as links to the project route.
    const links = screen.getAllByRole('link').filter((l) =>
      l.getAttribute('href')?.startsWith('/project/'),
    )
    expect(links.some((l) => l.getAttribute('href') === '/project/vesa-mount')).toBe(true)
    expect(links.some((l) => l.getAttribute('href') === '/project/monitor-arm')).toBe(true)
    expect(links.some((l) => l.getAttribute('href') === '/project/wall-plate')).toBe(true)

    // Member slug is humanized into a readable name.
    expect(screen.getByText('Vesa Mount')).toBeInTheDocument()
  })

  it('expanding a second family collapses the first (single-open accordion)', async () => {
    mockFetch()
    renderWithProviders(<StandardsBrowser />)
    await waitForDirectory()

    const vesaButton = screen.getByRole('button', { name: /VESA/ })
    const uncButton = screen.getByRole('button', { name: /1\/4-20 UNC/ })

    fireEvent.click(vesaButton)
    await waitFor(() => expect(screen.getByText('Vesa Mount')).toBeInTheDocument())

    fireEvent.click(uncButton)
    await waitFor(() => {
      expect(uncButton).toHaveAttribute('aria-expanded', 'true')
    })
    // First family's members are gone once the second opens.
    expect(screen.queryByText('Vesa Mount')).not.toBeInTheDocument()
    expect(screen.getByText('Tripod Plate')).toBeInTheDocument()
  })

  it('clicking an expanded family again collapses it', async () => {
    mockFetch()
    renderWithProviders(<StandardsBrowser />)
    await waitForDirectory()

    const vesaButton = screen.getByRole('button', { name: /VESA/ })
    fireEvent.click(vesaButton)
    await waitFor(() => expect(screen.getByText('Vesa Mount')).toBeInTheDocument())

    fireEvent.click(vesaButton)
    await waitFor(() => {
      expect(vesaButton).toHaveAttribute('aria-expanded', 'false')
    })
    expect(screen.queryByText('Vesa Mount')).not.toBeInTheDocument()
  })

  it('renders the empty state when no families are returned', async () => {
    mockFetch(buildFamiliesResponse([]))
    renderWithProviders(<StandardsBrowser />)
    await waitFor(() => {
      expect(
        screen.getByText('No standard families found in the catalog yet.'),
      ).toBeInTheDocument()
    })
  })

  it('shows an empty-family note when an expanded family has no members', async () => {
    mockFetch(buildFamiliesResponse([{ family: 'vesa', members: 0, slugs: [] }]))
    renderWithProviders(<StandardsBrowser />)
    await waitForDirectory()

    fireEvent.click(screen.getByRole('button', { name: /VESA/ }))
    await waitFor(() => {
      expect(screen.getByText('No objects in this family yet.')).toBeInTheDocument()
    })
  })

  it('renders the error state with a Retry button and recovers on retry', async () => {
    // Only the families endpoint fails; the provider chain's manifest/projects
    // fetches still resolve so the wrapping providers render normally.
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = url.toString()
      if (u.includes('/manifest')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(fallbackManifest) })
      }
      if (u.includes('/api/catalog/families')) {
        return Promise.reject(new Error('Network error'))
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
    })
    renderWithProviders(<StandardsBrowser />)
    await waitFor(() => {
      expect(screen.getByText("Couldn't load standards")).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()

    // Now let the families endpoint succeed and click Retry.
    spy.mockImplementation((url) => {
      const u = url.toString()
      if (u.includes('/manifest')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(fallbackManifest) })
      }
      if (u.includes('/api/catalog/families')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(buildFamiliesResponse()) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
    })
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

    await waitForDirectory()
  })

  it('renders the error state on a non-OK HTTP status', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = url.toString()
      if (u.includes('/manifest')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(fallbackManifest) })
      }
      if (u.includes('/api/catalog/families')) {
        return Promise.resolve({ ok: false, status: 500 })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
    })
    renderWithProviders(<StandardsBrowser />)
    await waitFor(() => {
      expect(screen.getByText("Couldn't load standards")).toBeInTheDocument()
    })
  })

  // --- Localized labels (Spanish) ---

  it('renders the Spanish title and member label', async () => {
    mockFetch()
    renderWithProviders(<StandardsBrowser />, { language: 'es' })
    // The heading renders in every state (incl. loading), so wait on loaded
    // content — the localized member count — before asserting.
    await waitFor(() => {
      expect(screen.getByText('3 objetos')).toBeInTheDocument()
    })
    expect(screen.getByRole('heading', { name: /Explorar por estándar/ })).toBeInTheDocument()
  })

  // --- Accessibility ---

  it('has no axe a11y violations (collapsed)', { timeout: 15000 }, async () => {
    mockFetch()
    const { container } = renderWithProviders(<StandardsBrowser />)
    await waitForDirectory()
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  it('has no axe a11y violations (expanded members)', { timeout: 15000 }, async () => {
    mockFetch()
    const { container } = renderWithProviders(<StandardsBrowser />)
    await waitForDirectory()
    fireEvent.click(screen.getByRole('button', { name: /VESA/ }))
    await waitFor(() => expect(screen.getByText('Vesa Mount')).toBeInTheDocument())
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
