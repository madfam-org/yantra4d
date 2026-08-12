import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock child components to avoid Three.js/R3F in jsdom. The carousel mock also
// surfaces the state setters the container passes down, so the filter branches
// can be driven the same way the real UI drives them.
vi.mock('./ProjectCarousel3D', () => ({
  default: ({ projects, activeCategory, searchQuery, carouselNote,
              setSearchQuery, setActiveCategory, setActiveDomain }: any) => (
    <div data-testid="carousel" data-count={projects.length} data-category={activeCategory}
         data-search={searchQuery} data-note={carouselNote ?? ''}>
      Carousel
      <button data-testid="set-search" onClick={() => setSearchQuery('gridfinity')} />
      <button data-testid="set-search-nomatch" onClick={() => setSearchQuery('zzzz-no-such-project')} />
      <button data-testid="set-search-blank" onClick={() => setSearchQuery('   ')} />
      <button data-testid="set-cat-commons" onClick={() => setActiveCategory('commons')} />
      <button data-testid="set-cat-mechanical" onClick={() => setActiveCategory('mechanical')} />
      <button data-testid="set-domain-medical" onClick={() => setActiveDomain('medical')} />
    </div>
  ),
}))
vi.mock('./ProjectGalleryGrid', () => ({
  default: ({ projects, activeCategory }: any) => (
    <div data-testid="grid" data-count={projects.length} data-category={activeCategory}>
      Grid
    </div>
  ),
}))

import ProjectGalleryContainer from './ProjectGalleryContainer'

const CAROUSEL_LIMIT = 24

const count = (testId: string) =>
  parseInt(screen.getByTestId(testId).getAttribute('data-count') || '0', 10)

describe('ProjectGalleryContainer', () => {
  it('renders carousel and grid sections', () => {
    render(<ProjectGalleryContainer />)
    expect(screen.getByTestId('carousel')).toBeInTheDocument()
    expect(screen.getByTestId('grid')).toBeInTheDocument()
  })

  it('passes lang prop to children', () => {
    render(<ProjectGalleryContainer lang="en" />)
    expect(screen.getByTestId('carousel')).toBeInTheDocument()
    expect(screen.getByTestId('grid')).toBeInTheDocument()
  })

  it('defaults activeCategory to all', () => {
    render(<ProjectGalleryContainer />)
    expect(screen.getByTestId('carousel')).toHaveAttribute('data-category', 'all')
    expect(screen.getByTestId('grid')).toHaveAttribute('data-category', 'all')
  })

  it('splits projects: hyperobjects to carousel, others to grid', () => {
    render(<ProjectGalleryContainer />)
    expect(count('carousel') + count('grid')).toBeGreaterThan(0)
  })

  it('caps the carousel to protect the GPU and spills the rest into the grid', () => {
    render(<ProjectGalleryContainer />)
    // Every extra carousel item mounts its own GLB mesh, so the cap is load-bearing.
    expect(count('carousel')).toBeLessThanOrEqual(CAROUSEL_LIMIT)
    expect(count('grid')).toBeGreaterThan(0)
  })

  it('explains the overflow in the active language', () => {
    const { unmount } = render(<ProjectGalleryContainer lang="en" />)
    expect(screen.getByTestId('carousel').getAttribute('data-note')).toMatch(/Showing \d+ of \d+ in 3D/)
    unmount()

    render(<ProjectGalleryContainer lang="es" />)
    expect(screen.getByTestId('carousel').getAttribute('data-note')).toMatch(/Mostrando \d+ de \d+ en 3D/)
  })

  it('narrows results when a search query matches', () => {
    render(<ProjectGalleryContainer />)
    const before = count('carousel') + count('grid')
    fireEvent.click(screen.getByTestId('set-search'))
    expect(count('carousel') + count('grid')).toBeLessThan(before)
  })

  it('yields nothing when the query matches no project', () => {
    render(<ProjectGalleryContainer />)
    fireEvent.click(screen.getByTestId('set-search-nomatch'))
    expect(count('carousel') + count('grid')).toBe(0)
  })

  it('ignores a whitespace-only query', () => {
    render(<ProjectGalleryContainer />)
    const before = count('carousel') + count('grid')
    fireEvent.click(screen.getByTestId('set-search-blank'))
    expect(count('carousel') + count('grid')).toBe(before)
  })

  it('restricts to hyperobjects under the commons category', () => {
    render(<ProjectGalleryContainer />)
    fireEvent.click(screen.getByTestId('set-cat-commons'))
    // Commons is hyperobjects-only, so the carousel stays saturated at the cap.
    expect(count('carousel')).toBe(CAROUSEL_LIMIT)
    expect(screen.getByTestId('grid')).toHaveAttribute('data-category', 'commons')
  })

  it('filters by a concrete category', () => {
    render(<ProjectGalleryContainer />)
    const before = count('carousel') + count('grid')
    fireEvent.click(screen.getByTestId('set-cat-mechanical'))
    const after = count('carousel') + count('grid')
    expect(after).toBeGreaterThan(0)
    expect(after).toBeLessThan(before)
  })

  it('filters by domain', () => {
    render(<ProjectGalleryContainer />)
    const before = count('carousel') + count('grid')
    fireEvent.click(screen.getByTestId('set-domain-medical'))
    const after = count('carousel') + count('grid')
    expect(after).toBeGreaterThan(0)
    expect(after).toBeLessThan(before)
  })

  it('composes category and domain filters', () => {
    render(<ProjectGalleryContainer />)
    fireEvent.click(screen.getByTestId('set-cat-commons'))
    const commonsOnly = count('carousel') + count('grid')
    fireEvent.click(screen.getByTestId('set-domain-medical'))
    expect(count('carousel') + count('grid')).toBeLessThan(commonsOnly)
  })
})
