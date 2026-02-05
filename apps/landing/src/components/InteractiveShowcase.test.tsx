import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import InteractiveShowcase from './InteractiveShowcase'

// Stub import.meta.env.DEV
vi.stubGlobal('import', { meta: { env: { DEV: true } } })

describe('InteractiveShowcase', () => {
  it('renders all project tabs', () => {
    render(<InteractiveShowcase />)
    expect(screen.getByRole('tablist', { name: 'Demo projects' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Gridfinity' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Voronoi' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Gear Reducer' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'PolyDice' })).toBeInTheDocument()
  })

  it('first tab is selected by default', () => {
    render(<InteractiveShowcase />)
    const gridfinityTab = screen.getByRole('tab', { name: 'Gridfinity' })
    expect(gridfinityTab).toHaveAttribute('aria-selected', 'true')
  })

  it('renders iframe with correct src for active project', () => {
    render(<InteractiveShowcase />)
    const iframe = screen.getByTitle('Gridfinity interactive demo')
    expect(iframe).toBeInTheDocument()
    expect(iframe).toHaveAttribute('src', expect.stringContaining('gridfinity'))
  })

  it('switches active project on tab click', () => {
    render(<InteractiveShowcase />)
    fireEvent.click(screen.getByRole('tab', { name: 'Voronoi' }))

    expect(screen.getByRole('tab', { name: 'Voronoi' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Gridfinity' })).toHaveAttribute('aria-selected', 'false')
    expect(screen.getByTitle('Voronoi interactive demo')).toBeInTheDocument()
  })

  it('updates iframe src when switching tabs', () => {
    render(<InteractiveShowcase />)
    fireEvent.click(screen.getByRole('tab', { name: 'PolyDice' }))
    const iframe = screen.getByTitle('PolyDice interactive demo')
    expect(iframe).toHaveAttribute('src', expect.stringContaining('polydice'))
  })

  it('shows project description', () => {
    render(<InteractiveShowcase />)
    const descriptions = screen.getAllByText(/Modular storage bins/)
    expect(descriptions.length).toBeGreaterThan(0)
  })

  it('shows category badge', () => {
    render(<InteractiveShowcase />)
    expect(screen.getByText('Storage')).toBeInTheDocument()
  })

  it('has tabpanel with correct aria attributes', () => {
    render(<InteractiveShowcase />)
    const panel = screen.getByRole('tabpanel')
    expect(panel).toHaveAttribute('aria-labelledby', 'tab-gridfinity')
  })

  it('updates tabpanel labelledby when switching tabs', () => {
    render(<InteractiveShowcase />)
    fireEvent.click(screen.getByRole('tab', { name: 'Maze' }))
    const panel = screen.getByRole('tabpanel')
    expect(panel).toHaveAttribute('aria-labelledby', 'tab-maze')
  })

  it('has live region for screen readers', () => {
    const { container } = render(<InteractiveShowcase />)
    const liveRegion = container.querySelector('[aria-live="polite"]')
    expect(liveRegion).toBeInTheDocument()
    expect(liveRegion?.textContent).toContain('Modular storage bins')
  })

  it('shows "Open in Studio" link', () => {
    render(<InteractiveShowcase />)
    const link = screen.getByText(/Open Gridfinity in Studio/)
    expect(link).toHaveAttribute('href', expect.stringContaining('gridfinity'))
    expect(link).toHaveAttribute('target', '_blank')
  })
})
