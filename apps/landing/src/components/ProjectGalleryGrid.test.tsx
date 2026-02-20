import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ProjectGalleryGrid from './ProjectGalleryGrid'

// Stub import.meta.env.DEV
vi.stubGlobal('import', { meta: { env: { DEV: true } } })

describe('ProjectGalleryGrid', () => {
  it('renders category filter tabs', () => {
    render(<ProjectGalleryGrid />)
    expect(screen.getByRole('tablist', { name: 'Project categories' })).toBeInTheDocument()
    // Default lang=es so we get Spanish labels
    expect(screen.getByRole('tab', { name: 'Todos' })).toBeInTheDocument()
  })

  it('renders all projects by default', () => {
    render(<ProjectGalleryGrid />)
    // Should have project cards for all projects
    expect(screen.getAllByText('Gridfinity Extended').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Voronoi Generator').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Gear Reducer').length).toBeGreaterThan(0)
  })

  it('filters by category when clicking tab', () => {
    render(<ProjectGalleryGrid />)
    fireEvent.click(screen.getByRole('tab', { name: 'Mecánico' }))

    // Should show mechanical projects
    expect(screen.getAllByText('Gear Reducer').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Parametric Gears').length).toBeGreaterThan(0)

    // Should not show non-mechanical projects
    expect(screen.queryByText('Voronoi Generator')).not.toBeInTheDocument()
  })

  it('shows all projects when clicking "all" filter', () => {
    render(<ProjectGalleryGrid />)
    // First filter to a category
    fireEvent.click(screen.getByRole('tab', { name: 'Mecánico' }))
    expect(screen.queryByText('Voronoi Generator')).not.toBeInTheDocument()

    // Click all
    fireEvent.click(screen.getByRole('tab', { name: 'Todos' }))
    expect(screen.getAllByText('Voronoi Generator').length).toBeGreaterThan(0)
  })

  it('shows Spanish descriptions by default (lang=es)', () => {
    render(<ProjectGalleryGrid />)
    expect(screen.getByText(/Contenedores modulares/)).toBeInTheDocument()
  })

  it('shows English descriptions when lang=en', () => {
    render(<ProjectGalleryGrid lang="en" />)
    expect(screen.getByText(/Modular storage bins/)).toBeInTheDocument()
  })

  it('renders project cards with images', () => {
    render(<ProjectGalleryGrid />)
    const images = screen.getAllByRole('img')
    expect(images.length).toBeGreaterThan(0)
    expect(images[0]).toHaveAttribute('loading', 'lazy')
    expect(images[0]).toHaveAttribute('width', '640')
    expect(images[0]).toHaveAttribute('height', '360')
  })

  it('project cards link to studio', () => {
    render(<ProjectGalleryGrid />)
    const links = screen.getAllByRole('link')
    expect(links.length).toBeGreaterThan(0)
    expect(links[0]).toHaveAttribute('href', expect.stringContaining('gridfinity'))
    expect(links[0]).toHaveAttribute('target', '_blank')
    expect(links[0]).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('shows category badge on each project card', () => {
    render(<ProjectGalleryGrid />)
    // Each project card should have its category label
    const badges = screen.getAllByText('Almacenamiento')
    expect(badges.length).toBeGreaterThan(0)
  })

  it('shows "Open in Studio" text on cards', () => {
    render(<ProjectGalleryGrid />)
    const openLabels = screen.getAllByText('Abrir en Studio →')
    expect(openLabels.length).toBeGreaterThan(0)
  })

  it('uses custom translations when provided', () => {
    const t = {
      gallery: {
        categories: {
          all: 'All',
          storage: 'Storage',
          mechanical: 'Mechanical',
          art: 'Art & Generative',
          tabletop: 'Tabletop',
          education: 'Education',
          electronics: 'Electronics',
        },
        openInStudio: 'Open in Studio →',
      },
    } as any

    render(<ProjectGalleryGrid lang="en" t={t} />)
    expect(screen.getByRole('tab', { name: 'All' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Storage' })).toBeInTheDocument()
  })

  it('highlights active category tab', () => {
    render(<ProjectGalleryGrid />)
    const allTab = screen.getByRole('tab', { name: 'Todos' })
    expect(allTab).toHaveAttribute('aria-selected', 'true')

    fireEvent.click(screen.getByRole('tab', { name: 'Mecánico' }))
    expect(screen.getByRole('tab', { name: 'Mecánico' })).toHaveAttribute('aria-selected', 'true')
    expect(allTab).toHaveAttribute('aria-selected', 'false')
  })

  it('renders Commons category tab', () => {
    render(<ProjectGalleryGrid />)
    const commonsTab = screen.getByRole('tab', { name: '🔷 Commons' })
    expect(commonsTab).toBeInTheDocument()
  })

  it('filters to hyperobject projects when Commons tab is clicked', () => {
    render(<ProjectGalleryGrid />)
    fireEvent.click(screen.getByRole('tab', { name: '🔷 Commons' }))

    // hyperobject projects should be visible
    expect(screen.getAllByText('Microscope Slide Holder').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Gridfinity Extended').length).toBeGreaterThan(0)
    // non-hyperobject projects should be hidden
    expect(screen.queryByText('Voronoi Generator')).not.toBeInTheDocument()
    expect(screen.queryByText('PolyDice Generator')).not.toBeInTheDocument()
  })

  it('renders hyperobject badge on hyperobject cards', () => {
    render(<ProjectGalleryGrid />)
    // The slide-holder card should display the Hyperobject badge
    const badges = screen.getAllByText(/Hyperobject/)
    expect(badges.length).toBeGreaterThan(0)
  })

  it('shows domain label on hyperobject cards', () => {
    render(<ProjectGalleryGrid />)
    // slide-holder has domain: 'medical' → shows 'Médico' in Spanish (default lang)
    expect(screen.getAllByText('Médico').length).toBeGreaterThan(0)
  })
})
