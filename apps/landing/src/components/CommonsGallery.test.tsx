import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'
import { CAROUSEL_LIMIT, PAGE_SIZE, type GalleryItem } from '../lib/gallery'

// The 3D stage is mocked: it is lazily imported by the island, and the test
// cares about WHEN it is asked for, not what it draws.
vi.mock('./ProjectCarousel3D', () => ({
  default: (props: any) => (
    <div
      data-testid="commons-stage"
      data-count={props.projects.length}
      data-note={props.note ?? ''}
      data-manifest={props.manifest ? 'yes' : 'no'}
      data-tier={props.tier}
    >
      Stage
    </div>
  ),
}))
vi.mock('./ProjectGalleryGrid', () => ({
  default: (props: any) => (
    <div data-testid="grid" data-count={props.projects.length} data-slugs={props.projects.map((p: any) => p.slug).join(',')}>
      Grid
    </div>
  ),
}))

import CommonsGallery, { type GalleryLabels } from './CommonsGallery'

const LABELS: GalleryLabels = {
  search: 'Search',
  allCategories: 'All categories',
  allDomains: 'All domains',
  showMore: 'Show more',
  showing: 'Showing {shown} of {total}',
  inThreeD: 'Showing {shown} of {total} in 3D — browse all below',
  noResults: 'No hyperobjects found.',
  openStudio: 'Open Studio',
  openInStudio: 'Open in Studio →',
  swipe: 'Swipe',
  drag: 'Drag',
  prev: 'Prev',
  next: 'Next',
  live: 'Live',
  stillStrip: 'A selection',
  hyperobject: 'Hyperobject',
  loading: 'Loading…',
  categories: { all: 'All', commons: 'Commons', storage: 'Storage', mechanical: 'Mechanical', art: 'Art' },
  domains: { household: 'Household', medical: 'Medical' },
}

const TOTAL = 80
const ALL: GalleryItem[] = Array.from({ length: TOTAL }, (_, i) => ({
  slug: `item-${i}`,
  name: i === 0 ? 'Gridfinity Bin' : `Item ${i}`,
  description: i < 10 ? 'medical grade' : 'general purpose',
  category: i % 3 === 0 ? 'storage' : 'mechanical',
  thumbnail: `/projects/item-${i}.webp`,
  isHyperobject: i % 4 !== 3,
  domain: i < 10 ? 'medical' : 'household',
}))
const MODELLED = ALL.slice(0, 5).map((p) => p.slug)
// The server's pick: modelled hyperobjects first, then fill with unmodelled hyperobjects.
const STAGE = [
  ...ALL.filter((p) => p.isHyperobject && MODELLED.includes(p.slug)),
  ...ALL.filter((p) => !p.isHyperobject && MODELLED.includes(p.slug)),
  ...ALL.filter((p) => p.isHyperobject && !MODELLED.includes(p.slug)),
].slice(0, CAROUSEL_LIMIT)

const DATA_URL = '/data/en/commons.json'
const MANIFEST_URL = '/models/manifest.json'

function mountSsrNeighbours() {
  const ssr = document.createElement('div')
  ssr.setAttribute('data-testid', 'commons-grid')
  const more = document.createElement('a')
  more.setAttribute('data-testid', 'commons-more')
  more.href = '#'
  document.body.append(ssr, more)
  return { ssr, more }
}

function renderIsland(tier: 'still' | 'lite' | 'full') {
  return render(
    <CommonsGallery
      lang="en"
      labels={LABELS}
      stage={STAGE}
      modelled={MODELLED}
      total={TOTAL}
      categories={['all', 'commons', 'storage', 'mechanical', 'art']}
      domains={['medical', 'household']}
      dataUrl={DATA_URL}
      manifestUrl={MANIFEST_URL}
      studioUrl="https://app.example.test"
      forcedTier={tier}
    />,
  )
}

const calls = (spy: ReturnType<typeof vi.spyOn>, url: string) =>
  spy.mock.calls.filter((c) => String(c[0]) === url).length

describe('CommonsGallery', () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: any) => {
      const url = String(input)
      if (url === MANIFEST_URL) return { ok: true, json: async () => ({ version: 2, models: MODELLED.map((slug) => ({ slug, size: 1 })) }) } as Response
      if (url === DATA_URL) return { ok: true, json: async () => ({ items: ALL }) } as Response
      return { ok: false, json: async () => ({}) } as Response
    })
  })
  afterEach(() => {
    cleanup()
    fetchSpy.mockRestore()
    document.body.innerHTML = ''
  })

  it('still tier: shows the thumbnail strip, never the stage, and fetches nothing', () => {
    renderIsland('still')
    expect(screen.getByTestId('commons-still')).toBeInTheDocument()
    expect(screen.queryByTestId('commons-stage')).not.toBeInTheDocument()
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('lite tier: loads the stage lazily with the mesh manifest', async () => {
    renderIsland('lite')
    const stage = await screen.findByTestId('commons-stage')
    expect(stage).toHaveAttribute('data-count', String(STAGE.length))
    expect(stage).toHaveAttribute('data-tier', 'lite')
    await waitFor(() => expect(stage).toHaveAttribute('data-manifest', 'yes'))
    expect(calls(fetchSpy, MANIFEST_URL)).toBe(1)
    expect(calls(fetchSpy, DATA_URL)).toBe(0)
  })

  it('fetches the commons list once, on the first search, and filters from it', async () => {
    renderIsland('still')
    const search = screen.getByTestId('commons-search') as HTMLInputElement
    fireEvent.change(search, { target: { value: 'medical' } })
    await waitFor(() => expect(calls(fetchSpy, DATA_URL)).toBe(1))
    // 10 medical items, 8 of them hyperobjects (i % 4 !== 3): all fit on the stage.
    await waitFor(() => expect(screen.getByTestId('commons-still')).toBeInTheDocument())
    fireEvent.change(search, { target: { value: 'Gridfinity' } })
    await waitFor(() => expect(screen.queryByTestId('commons-empty')).not.toBeInTheDocument())
    expect(calls(fetchSpy, DATA_URL)).toBe(1)
  })

  it('shows the empty state when nothing matches', async () => {
    renderIsland('still')
    fireEvent.change(screen.getByTestId('commons-search'), { target: { value: 'zzzz-no-such-thing' } })
    expect(await screen.findByTestId('commons-empty')).toHaveTextContent('No hyperobjects found.')
  })

  it('hides the server-rendered first page while a filter is active, and restores it', async () => {
    const { ssr, more } = mountSsrNeighbours()
    renderIsland('still')
    fireEvent.change(screen.getByTestId('commons-search'), { target: { value: 'general' } })
    await waitFor(() => expect(ssr.hidden).toBe(true))
    expect(more.hidden).toBe(true)
    fireEvent.change(screen.getByTestId('commons-search'), { target: { value: '' } })
    await waitFor(() => expect(ssr.hidden).toBe(false))
  })

  it('"show more" pages past the server-rendered first page without duplicating it', async () => {
    const { more } = mountSsrNeighbours()
    renderIsland('still')
    expect(screen.queryByTestId('commons-grid-more')).not.toBeInTheDocument()
    fireEvent.click(more)
    const dyn = await screen.findByTestId('grid')
    // 80 total − 24 on the stage = 56 in the grid; page 1 (24) is SSR, page 2 is ours.
    expect(dyn).toHaveAttribute('data-count', String(Math.min(PAGE_SIZE, TOTAL - CAROUSEL_LIMIT - PAGE_SIZE)))
    const shown = dyn.getAttribute('data-slugs')!.split(',')
    const stageSlugs = new Set(STAGE.map((p) => p.slug))
    expect(shown.some((s) => stageSlugs.has(s))).toBe(false)
    expect(calls(fetchSpy, DATA_URL)).toBe(1)
  })

  it('tells the visitor how much of a result set is on the stage', async () => {
    renderIsland('full')
    fireEvent.change(screen.getByTestId('commons-search'), { target: { value: 'general' } })
    const stage = await screen.findByTestId('commons-stage')
    await waitFor(() => expect(stage.getAttribute('data-note')).toMatch(/^Showing \d+ of \d+ in 3D/))
  })

  it('category "commons" keeps hyperobjects only', async () => {
    renderIsland('still')
    const select = screen.getByLabelText('All categories') as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'commons' } })
    await waitFor(() => expect(calls(fetchSpy, DATA_URL)).toBe(1))
    // 60 hyperobjects → 24 on the stage, 36 in the grid → first page of 24 rendered by the island.
    const dyn = await screen.findByTestId('grid')
    expect(dyn).toHaveAttribute('data-count', String(PAGE_SIZE))
  })
})
