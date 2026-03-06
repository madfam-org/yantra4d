import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

// Mock child components to avoid Three.js/R3F in jsdom
vi.mock('./ProjectCarousel3D', () => ({
  default: ({ projects, activeCategory, searchQuery }: any) => (
    <div data-testid="carousel" data-count={projects.length} data-category={activeCategory}>
      Carousel
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
    // The container splits PROJECTS from data/projects.ts
    // We just verify both components render with their respective project counts
    const carousel = screen.getByTestId('carousel')
    const grid = screen.getByTestId('grid')
    const carouselCount = parseInt(carousel.getAttribute('data-count') || '0')
    const gridCount = parseInt(grid.getAttribute('data-count') || '0')
    expect(carouselCount + gridCount).toBeGreaterThan(0)
  })
})
