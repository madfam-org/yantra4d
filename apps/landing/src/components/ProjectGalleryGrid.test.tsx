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
    expect(screen.getByText('Gridfinity Extended')).toBeInTheDocument()
    expect(screen.getByText('Voronoi Generator')).toBeInTheDocument()
    expect(screen.getByText('Gear Reducer')).toBeInTheDocument()
  })

  it('filters by category when clicking tab', () => {
    render(<ProjectGalleryGrid />)
    fireEvent.click(screen.getByRole('tab', { name: 'Mecánico' }))

    // Should show mechanical projects
    expect(screen.getByText('Gear Reducer')).toBeInTheDocument()
    expect(screen.getByText('Parametric Gears')).toBeInTheDocument()

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
    expect(screen.getByText('Voronoi Generator')).toBeInTheDocument()
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
})
