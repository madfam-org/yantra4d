import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import Controls from './Controls'
import { renderWithProviders } from '../../test/render-with-providers'
// eslint-disable-next-line no-unused-vars
import fallbackManifest from '../../config/fallback-manifest.json'

expect.extend(toHaveNoViolations)

// Wrap with required providers
function renderControls(props = {}) {
  const defaultProps = {
    params: {
      width_units: 2, depth_units: 1, height_units: 3,
      cup_wall_thickness: 0, cup_floor_thickness: 0.7,
      vertical_chambers: 1, horizontal_chambers: 1,
      fingerslide_enabled: false, label_enabled: false,
      enable_magnets: false, enable_screws: false,
      fn: 0,
    },
    setParams: vi.fn(),
    mode: 'cup',
    colors: { cup: '#4a90d9' },
    setColors: vi.fn(),
  }

  // ManifestProvider fetches manifest on mount; mock fetch to fail so it uses fallback
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('no backend'))

  return renderWithProviders(<Controls {...defaultProps} {...props} />)
}

describe('Controls', () => {
  it('renders slider labels for cup mode parameters', () => {
    renderControls()
    expect(screen.getByText('Width (units)')).toBeInTheDocument()
    expect(screen.getByText('Depth (units)')).toBeInTheDocument()
    expect(screen.getByText('Height (units)')).toBeInTheDocument()
  })

  it('renders color picker for cup mode (cup part)', () => {
    renderControls()
    const colorInput = screen.getByDisplayValue('#4a90d9')
    expect(colorInput).toBeInTheDocument()
    expect(colorInput).toHaveAttribute('type', 'color')
  })

  it('color change calls setColors', () => {
    const setColors = vi.fn()
    renderControls({ setColors })
    const colorInput = screen.getByDisplayValue('#4a90d9')
    fireEvent.change(colorInput, { target: { value: '#ff0000' } })
    expect(setColors).toHaveBeenCalled()
  })

  it('renders baseplate parameters when mode is baseplate', () => {
    renderControls({
      mode: 'baseplate',
      params: {
        width_units: 2, depth_units: 2,
        bp_enable_magnets: false, bp_enable_screws: false,
        bp_corner_radius: 3.75, bp_reduced_wall: -1,
        bp_reduced_wall_taper: false,
        fn: 0,
      },
    })
    expect(screen.getByText('Width (units)')).toBeInTheDocument()
    expect(screen.getByText('Depth (units)')).toBeInTheDocument()
    expect(screen.getByText('Corner Radius (mm)')).toBeInTheDocument()
  })

  it('renders colors group label for part color controls', () => {
    renderControls()
    // Gridfinity has no "colors" parameter_group, so getGroupLabel returns raw id
    expect(screen.getByText('colors')).toBeInTheDocument()
  })

  it('sliders are labelled via aria-labelledby pointing to the parameter label', () => {
    renderControls()
    expect(screen.getByLabelText('Width (units)')).toBeInTheDocument()
    expect(screen.getByLabelText('Depth (units)')).toBeInTheDocument()
    expect(screen.getByLabelText('Height (units)')).toBeInTheDocument()
  })

  it('value displays have descriptive aria-label', () => {
    renderControls()
    const valueDisplay = screen.getByLabelText(/Width \(units\): 2\. (Click to edit|Clic para editar)/)
    expect(valueDisplay).toBeInTheDocument()
    expect(valueDisplay).toHaveAttribute('role', 'button')
    expect(valueDisplay).toHaveAttribute('tabIndex', '0')
  })

  it('renders default star indicators on slider tracks', () => {
    renderControls()
    expect(screen.getByTestId('default-star-width_units')).toBeInTheDocument()
    expect(screen.getByTestId('default-star-depth_units')).toBeInTheDocument()
    expect(screen.getByTestId('default-star-height_units')).toBeInTheDocument()
  })

  it('default star remains when value differs from default', () => {
    renderControls({
      params: {
        width_units: 4, depth_units: 1, height_units: 3,
        cup_wall_thickness: 0, cup_floor_thickness: 0.7,
        vertical_chambers: 1, horizontal_chambers: 1,
        fingerslide_enabled: false, label_enabled: false,
        enable_magnets: false, enable_screws: false,
        fn: 0,
      }
    })
    // Star should still be present even though width_units (4) != default (2)
    expect(screen.getByTestId('default-star-width_units')).toBeInTheDocument()
  })

  it('does not render color-gradient widget when manifest has no gradient params', () => {
    renderControls()
    // The fallback manifest (gridfinity) has no widget: { type: 'color-gradient' } params
    expect(screen.queryByLabelText(/Gradient preview/)).not.toBeInTheDocument()
  })

  it('has no a11y violations', { timeout: 15000 }, async () => {
    const { container } = renderControls()
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
