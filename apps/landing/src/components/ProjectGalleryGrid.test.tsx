import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ProjectGalleryGrid from './ProjectGalleryGrid'

// Stub import.meta.env.DEV
vi.stubGlobal('import', { meta: { env: { DEV: true } } })

const MOCK_PROJECTS = [
  { slug: 'gridfinity', name: 'Gridfinity Extended', category: 'storage', isHyperobject: true, description: 'Modular storage bins', descriptionEs: 'Contenedores modulares' },
  { slug: 'voronoi', name: 'Voronoi Generator', category: 'art', description: 'Voronoi patterns generating', descriptionEs: 'Generador Voronoi' },
  { slug: 'gear-reducer', name: 'Gear Reducer', category: 'mechanical', description: 'Parametric gears', descriptionEs: 'Engrane mecanico' },
  { slug: 'parametric-gears', name: 'Parametric Gears', category: 'mechanical', description: 'Gears', descriptionEs: 'Engranes' },
  { slug: 'slide-holder', name: 'Microscope Slide Holder', category: 'medical', isHyperobject: true, domain: 'medical' },
]

describe('ProjectGalleryGrid', () => {
  const defaultProps = {
    projects: MOCK_PROJECTS,
    activeCategory: 'all',
    setActiveCategory: vi.fn(),
  }

  it('renders category filter tabs', () => {
    render(<ProjectGalleryGrid {...defaultProps} />)
    expect(screen.getByRole('tablist', { name: 'Project categories' })).toBeInTheDocument()
    // Default lang=es so we get Spanish labels
    expect(screen.getByRole('tab', { name: 'Todos' })).toBeInTheDocument()
  })

  it('renders all projects by default', () => {
    render(<ProjectGalleryGrid {...defaultProps} />)
    // Should have project cards for all projects
    expect(screen.getAllByText('Gridfinity Extended').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Voronoi Generator').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Gear Reducer').length).toBeGreaterThan(0)
  })

  it('filters by category when clicking tab', () => {
    let activeCat = 'all'
    const setActive = vi.fn((c) => { activeCat = c })
    const { rerender } = render(<ProjectGalleryGrid {...defaultProps} setActiveCategory={setActive} />)

    fireEvent.click(screen.getByRole('tab', { name: 'Mecánico' }))
    expect(setActive).toHaveBeenCalledWith('mechanical')

    // Simulate re-render with new prop
    const filtered = MOCK_PROJECTS.filter(p => p.category === 'mechanical')
    rerender(<ProjectGalleryGrid {...defaultProps} activeCategory="mechanical" projects={filtered} setActiveCategory={setActive} />)

    // Should show mechanical projects
    expect(screen.getAllByText('Gear Reducer').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Parametric Gears').length).toBeGreaterThan(0)

    // Should not show non-mechanical projects
    expect(screen.queryByText('Voronoi Generator')).not.toBeInTheDocument()
  })

  it('shows all projects when clicking "all" filter', () => {
    let activeCat = 'mechanical'
    const setActive = vi.fn((c) => { activeCat = c })
    const filtered = MOCK_PROJECTS.filter(p => p.category === 'mechanical')
    const { rerender } = render(<ProjectGalleryGrid {...defaultProps} activeCategory="mechanical" projects={filtered} setActiveCategory={setActive} />)

    expect(screen.queryByText('Voronoi Generator')).not.toBeInTheDocument()

    // Click all
    fireEvent.click(screen.getByRole('tab', { name: 'Todos' }))
    expect(setActive).toHaveBeenCalledWith('all')

    rerender(<ProjectGalleryGrid {...defaultProps} activeCategory="all" projects={MOCK_PROJECTS} setActiveCategory={setActive} />)
    expect(screen.getAllByText('Voronoi Generator').length).toBeGreaterThan(0)
  })

  it('shows Spanish descriptions by default (lang=es)', () => {
    render(<ProjectGalleryGrid {...defaultProps} />)
    expect(screen.getByText(/Contenedores modulares/)).toBeInTheDocument()
  })

  it('shows English descriptions when lang=en', () => {
    render(<ProjectGalleryGrid {...defaultProps} lang="en" />)
    expect(screen.getByText(/Modular storage bins/)).toBeInTheDocument()
  })

  it('renders project cards with images', () => {
    render(<ProjectGalleryGrid {...defaultProps} />)
    const images = screen.getAllByRole('img')
    expect(images.length).toBeGreaterThan(0)
  })

  it('project cards link to studio', () => {
    render(<ProjectGalleryGrid {...defaultProps} />)
    const links = screen.getAllByRole('link')
    expect(links.length).toBeGreaterThan(0)
    expect(links[0]).toHaveAttribute('href', expect.stringContaining('gridfinity'))
    expect(links[0]).toHaveAttribute('target', '_blank')
    expect(links[0]).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('shows category badge on each project card', () => {
    render(<ProjectGalleryGrid {...defaultProps} />)
    // Gridfinity should have Almacenamiento label
    const badges = screen.getAllByText('Almacenamiento')
    expect(badges.length).toBeGreaterThan(0)
  })

  it('shows "Open in Studio" text on cards', () => {
    render(<ProjectGalleryGrid {...defaultProps} />)
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

    render(<ProjectGalleryGrid {...defaultProps} lang="en" t={t} />)
    expect(screen.getByRole('tab', { name: 'All' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Storage' })).toBeInTheDocument()
  })

  it('highlights active category tab', () => {
    // Note: The UI renders <button role="tab">. 'Almacenamiento' has 'aria-selected'="false".
    render(<ProjectGalleryGrid {...defaultProps} activeCategory="mechanical" />)
    const allTab = screen.getByRole('tab', { name: 'Todos' })
    expect(allTab).toHaveAttribute('aria-selected', 'false')
    const mechanicalTab = screen.getByRole('tab', { name: 'Mecánico' })
    expect(mechanicalTab).toHaveAttribute('aria-selected', 'true')
  })

  it('renders Commons category tab', () => {
    render(<ProjectGalleryGrid {...defaultProps} />)
    const commonsTab = screen.getByRole('tab', { name: /Commons/i })
    expect(commonsTab).toBeInTheDocument()
  })

  it('filters to hyperobject projects when Commons tab is clicked', () => {
    const setActive = vi.fn()
    const { rerender } = render(<ProjectGalleryGrid {...defaultProps} setActiveCategory={setActive} />)

    // Use getByRole matching exact text
    const commonsTab = screen.getByRole('tab', { name: /Commons/i })
    fireEvent.click(commonsTab)
    expect(setActive).toHaveBeenCalledWith('commons')

    const filtered = MOCK_PROJECTS.filter(p => p.isHyperobject)
    rerender(<ProjectGalleryGrid {...defaultProps} activeCategory="commons" projects={filtered} setActiveCategory={setActive} />)

    // hyperobject projects should be visible
    expect(screen.getAllByText('Microscope Slide Holder').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Gridfinity Extended').length).toBeGreaterThan(0)
    // non-hyperobject projects should be hidden
    expect(screen.queryByText('Voronoi Generator')).not.toBeInTheDocument()
  })

  it('renders hyperobject badge on hyperobject cards', () => {
    render(<ProjectGalleryGrid {...defaultProps} />)
    // The slide-holder card should display the Hyperobject badge
    const badges = screen.getAllByText(/Hyperobject/)
    expect(badges.length).toBeGreaterThan(0)
  })

  it('shows domain label on hyperobject cards', () => {
    render(<ProjectGalleryGrid {...defaultProps} />)
    // slide-holder has domain: 'medical' → shows 'Médico' in Spanish (default lang)
    expect(screen.getAllByText('Médico').length).toBeGreaterThan(0)
  })
})
