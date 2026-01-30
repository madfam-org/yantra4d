import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import Controls from './Controls'
import { renderWithProviders } from '../test/render-with-providers'

// Wrap with required providers
function renderControls(props = {}) {
  const defaultProps = {
    params: { size: 20, thick: 2.5, rod_D: 3, show_base: true, show_walls: true, show_mech: true },
    setParams: vi.fn(),
    mode: 'unit',
    colors: { main: '#e5e7eb' },
    setColors: vi.fn(),
  }

  // ManifestProvider fetches manifest on mount; mock fetch to fail so it uses fallback
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('no backend'))

  return renderWithProviders(<Controls {...defaultProps} {...props} />)
}

describe('Controls', () => {
  it('renders slider labels for unit mode parameters', () => {
    renderControls()
    expect(screen.getByText('Size (mm)')).toBeInTheDocument()
    expect(screen.getByText('Thickness (mm)')).toBeInTheDocument()
    expect(screen.getByText('Rod Diameter (mm)')).toBeInTheDocument()
  })

  it('renders visibility checkboxes', () => {
    renderControls()
    expect(screen.getByText('Base')).toBeInTheDocument()
    expect(screen.getByText('Walls')).toBeInTheDocument()
    expect(screen.getByText('Mechanism')).toBeInTheDocument()
  })

  it('renders color picker for unit mode (main part)', () => {
    renderControls()
    const colorInput = screen.getByDisplayValue('#e5e7eb')
    expect(colorInput).toBeInTheDocument()
    expect(colorInput).toHaveAttribute('type', 'color')
  })

  it('color change calls setColors', () => {
    const setColors = vi.fn()
    renderControls({ setColors })
    const colorInput = screen.getByDisplayValue('#e5e7eb')
    fireEvent.change(colorInput, { target: { value: '#ff0000' } })
    expect(setColors).toHaveBeenCalled()
  })

  it('renders grid parameters when mode is grid', () => {
    renderControls({
      mode: 'grid',
      params: { rows: 8, cols: 8, rod_extension: 10, show_base: true, show_walls: true, show_mech: true },
    })
    expect(screen.getByText('Rows')).toBeInTheDocument()
    expect(screen.getByText('Cols')).toBeInTheDocument()
  })

  it('renders manifest-driven group labels for visibility and colors', () => {
    renderControls()
    // These labels now come from manifest.parameter_groups, not hardcoded ternaries
    expect(screen.getByText('Visibility')).toBeInTheDocument()
    expect(screen.getByText('Colors')).toBeInTheDocument()
  })
})
