import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'

expect.extend(toHaveNoViolations)

// --- Mock the API surface (getApiBase + apiFetch) --------------------------
// apiFetch is the only sanctioned way to reach the backend; mocking it lets us
// drive every load state deterministically and assert refetch-on-retry.
vi.mock('../../services/core/backendDetection', () => ({
  getApiBase: () => 'http://api.test',
}))

const apiFetch = vi.fn()
vi.mock('../../services/core/apiClient', () => ({
  apiFetch: (...args) => apiFetch(...args),
}))

import WorksWithPanel from './WorksWithPanel'
import { LanguageProvider } from '../../contexts/system/LanguageProvider'
import { MemoryRouter } from 'react-router-dom'

/**
 * Lightweight wrapper: WorksWithPanel only needs a language context (for t())
 * and a router (for <Link>). We deliberately avoid renderWithProviders here so
 * we don't drag in the heavy Manifest/Project/Viewer providers.
 */
function renderPanel(ui, { initialEntries = ['/'] } = {}) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <LanguageProvider defaultLanguage="en" storageKey="test-lang">
        {ui}
      </LanguageProvider>
    </MemoryRouter>,
  )
}

/** A works-with response with two partners (one mates, one same-family). */
function buildResponse(overrides = {}) {
  return {
    slug: 'arca-plate',
    count: 2,
    partners: [
      {
        slug: 'nato-rail',
        name: 'NATO Rail & Clamp',
        domain: 'commercial',
        thumbnail: '/projects/nato-rail.svg',
        reasons: [
          {
            family: 'unc-1/4-20',
            kind: 'mates_with',
            via: 'ASME B1.1 1/4-20 UNC',
            geometry: 'bolt_pattern↔bolt_pattern',
          },
          {
            family: 'vesa-75',
            kind: 'same_family',
            via: 'VESA MIS-D 75',
            geometry: 'bolt_pattern↔bolt_pattern',
          },
        ],
      },
      {
        slug: 'gridfinity-bin',
        name: 'Gridfinity Bin',
        domain: 'storage',
        thumbnail: '/projects/gridfinity-bin.svg',
        reasons: [
          {
            family: 'gridfinity-42',
            kind: 'same_family',
            via: 'Gridfinity 42mm',
            geometry: 'grid↔grid',
          },
        ],
      },
    ],
    ...overrides,
  }
}

/** Resolve apiFetch once with a JSON body. */
function resolveOnceWith(body, ok = true, status = 200) {
  apiFetch.mockResolvedValueOnce({
    ok,
    status,
    json: () => Promise.resolve(body),
  })
}

beforeEach(() => {
  apiFetch.mockReset()
  localStorage.clear()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('WorksWithPanel', () => {
  it('fetches the works-with endpoint for the given slug via getApiBase', async () => {
    resolveOnceWith(buildResponse())
    renderPanel(<WorksWithPanel slug="arca-plate" />)
    await waitFor(() => expect(apiFetch).toHaveBeenCalled())
    expect(apiFetch).toHaveBeenCalledWith('http://api.test/api/catalog/arca-plate/works-with')
  })

  it('renders a row per partner from the API', async () => {
    resolveOnceWith(buildResponse())
    renderPanel(<WorksWithPanel slug="arca-plate" />)
    expect(await screen.findByText('NATO Rail & Clamp')).toBeInTheDocument()
    expect(screen.getByText('Gridfinity Bin')).toBeInTheDocument()
  })

  it('links each partner to /project/<partnerSlug>', async () => {
    resolveOnceWith(buildResponse())
    renderPanel(<WorksWithPanel slug="arca-plate" />)
    await screen.findByText('NATO Rail & Clamp')
    const links = screen.getAllByRole('link')
    const hrefs = links.map((l) => l.getAttribute('href'))
    expect(hrefs).toContain('/project/nato-rail')
    expect(hrefs).toContain('/project/gridfinity-bin')
  })

  it('shows the shared-standard badge from reasons[0].via', async () => {
    resolveOnceWith(buildResponse())
    renderPanel(<WorksWithPanel slug="arca-plate" />)
    expect(await screen.findByText('ASME B1.1 1/4-20 UNC')).toBeInTheDocument()
    expect(screen.getByText('Gridfinity 42mm')).toBeInTheDocument()
  })

  it('shows a "mates" indicator for mates_with and "same family" for same_family', async () => {
    resolveOnceWith(buildResponse())
    renderPanel(<WorksWithPanel slug="arca-plate" />)
    await screen.findByText('NATO Rail & Clamp')

    const nato = screen.getByText('NATO Rail & Clamp').closest('a')
    expect(within(nato).getByText('Mates')).toBeInTheDocument()

    const grid = screen.getByText('Gridfinity Bin').closest('a')
    expect(within(grid).getByText('Same family')).toBeInTheDocument()
  })

  it('shows a "+N more" indicator when a partner has multiple reasons', async () => {
    resolveOnceWith(buildResponse())
    renderPanel(<WorksWithPanel slug="arca-plate" />)
    await screen.findByText('NATO Rail & Clamp')
    // nato-rail has 2 reasons → +1 more; gridfinity-bin has 1 → no "more".
    expect(screen.getByText('+1 more shared standards')).toBeInTheDocument()
  })

  it('renders the subtitle with the partner count', async () => {
    resolveOnceWith(buildResponse())
    renderPanel(<WorksWithPanel slug="arca-plate" />)
    expect(
      await screen.findByText('2 objects share a standard with this one'),
    ).toBeInTheDocument()
  })

  it('renders the friendly empty state when count is 0', async () => {
    resolveOnceWith({ slug: 'lonely', count: 0, partners: [] })
    renderPanel(<WorksWithPanel slug="lonely" />)
    expect(
      await screen.findByText(/No catalogued companions yet/i),
    ).toBeInTheDocument()
    // No partner links in the empty state.
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('transitions from loading skeleton to loaded content', async () => {
    let resolveFetch
    apiFetch.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFetch = () => resolve({ ok: true, status: 200, json: () => Promise.resolve(buildResponse()) })
      }),
    )
    renderPanel(<WorksWithPanel slug="arca-plate" />)

    // Loading: sr-only label present, partner rows not yet.
    expect(screen.getByText('Loading companions…')).toBeInTheDocument()
    expect(screen.queryByText('NATO Rail & Clamp')).not.toBeInTheDocument()

    resolveFetch()
    expect(await screen.findByText('NATO Rail & Clamp')).toBeInTheDocument()
    expect(screen.queryByText('Loading companions…')).not.toBeInTheDocument()
  })

  it('shows a quiet error state and refetches on retry', async () => {
    // First attempt rejects → error state with retry button.
    apiFetch.mockRejectedValueOnce(new Error('network down'))
    renderPanel(<WorksWithPanel slug="arca-plate" />)

    expect(await screen.findByText("Couldn't load companions")).toBeInTheDocument()
    const retryBtn = screen.getByRole('button', { name: 'Retry' })

    // Second attempt (triggered by retry) succeeds.
    resolveOnceWith(buildResponse())
    fireEvent.click(retryBtn)

    expect(await screen.findByText('NATO Rail & Clamp')).toBeInTheDocument()
    expect(apiFetch).toHaveBeenCalledTimes(2)
  })

  it('treats a non-ok HTTP response as an error', async () => {
    resolveOnceWith({}, false, 500)
    renderPanel(<WorksWithPanel slug="arca-plate" />)
    expect(await screen.findByText("Couldn't load companions")).toBeInTheDocument()
  })

  it('refetches when the slug prop changes', async () => {
    resolveOnceWith(buildResponse())
    const { rerender } = renderPanel(<WorksWithPanel slug="arca-plate" />)
    await screen.findByText('NATO Rail & Clamp')

    resolveOnceWith({
      slug: 'other',
      count: 1,
      partners: [
        {
          slug: 'vesa-arm',
          name: 'VESA Arm',
          domain: 'commercial',
          thumbnail: '',
          reasons: [{ family: 'vesa', kind: 'mates_with', via: 'VESA 100', geometry: 'x' }],
        },
      ],
    })
    rerender(
      <MemoryRouter>
        <LanguageProvider defaultLanguage="en" storageKey="test-lang">
          <WorksWithPanel slug="other" />
        </LanguageProvider>
      </MemoryRouter>,
    )
    expect(await screen.findByText('VESA Arm')).toBeInTheDocument()
    expect(apiFetch).toHaveBeenLastCalledWith('http://api.test/api/catalog/other/works-with')
  })

  it('falls back to a gradient tile when a thumbnail fails to load', async () => {
    resolveOnceWith(buildResponse())
    const { container } = renderPanel(<WorksWithPanel slug="arca-plate" />)
    const img = await waitFor(() => {
      const el = container.querySelector('img')
      expect(el).toBeInTheDocument()
      return el
    })
    fireEvent.error(img)
    // After error, the broken <img> is replaced by the gradient initial tile.
    await waitFor(() => {
      expect(within(screen.getByText('NATO Rail & Clamp').closest('a')).queryByRole('img')).toBeNull()
    })
  })

  it('has no axe accessibility violations in the loaded state', async () => {
    resolveOnceWith(buildResponse())
    const { container } = renderPanel(<WorksWithPanel slug="arca-plate" />)
    await screen.findByText('NATO Rail & Clamp')
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  }, 15000)

  it('has no axe accessibility violations in the empty state', async () => {
    resolveOnceWith({ slug: 'lonely', count: 0, partners: [] })
    const { container } = renderPanel(<WorksWithPanel slug="lonely" />)
    await screen.findByText(/No catalogued companions yet/i)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  }, 15000)
})
