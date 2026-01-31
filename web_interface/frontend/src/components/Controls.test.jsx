import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import Controls from './Controls'
import { renderWithProviders } from '../test/render-with-providers'
// eslint-disable-next-line no-unused-vars
import fallbackManifest from '../config/fallback-manifest.json'

// Wrap with required providers
function renderControls(props = {}) {
  const defaultProps = {
    params: {
      size: 20, thick: 2.5, rod_D: 3,
      show_base: true, show_walls: true, show_mech: true, show_letter: true,
      show_wall_left: true, show_wall_right: true,
      show_mech_base_ring: true, show_mech_pillars: true, show_mech_snap_beams: true,
    },
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
      params: {
        rows: 8, cols: 8, rod_extension: 10,
        show_base: true, show_walls: true, show_mech: true, show_letter: true,
        show_bottom: true, show_top: true, show_rods: true, show_stoppers: true,
        show_wall_left: true, show_wall_right: true,
        show_mech_base_ring: true, show_mech_pillars: true, show_mech_snap_beams: true,
        show_bottom_base: true, show_bottom_walls: true, show_bottom_mech: true, show_bottom_letter: true,
        show_bottom_wall_left: true, show_bottom_wall_right: true,
        show_bottom_mech_base_ring: true, show_bottom_mech_pillars: true, show_bottom_mech_snap_beams: true,
        show_top_base: true, show_top_walls: true, show_top_mech: true, show_top_letter: true,
        show_top_wall_left: true, show_top_wall_right: true,
        show_top_mech_base_ring: true, show_top_mech_pillars: true, show_top_mech_snap_beams: true,
      },
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

  it('does not show advanced visibility params in basic mode', () => {
    renderControls()
    // Advanced params should be hidden by default (basic mode)
    expect(screen.queryByText('Left Wall')).not.toBeInTheDocument()
    expect(screen.queryByText('Right Wall')).not.toBeInTheDocument()
    expect(screen.queryByText('Base Ring')).not.toBeInTheDocument()
    expect(screen.queryByText('Pillars')).not.toBeInTheDocument()
    expect(screen.queryByText('Snap Beams')).not.toBeInTheDocument()
  })

  it('shows advanced visibility params after toggling to Advanced', () => {
    renderControls()
    // Click the "Advanced" toggle button
    const advancedBtn = screen.getByText('Advanced')
    fireEvent.click(advancedBtn)

    // Now advanced params should be visible
    expect(screen.getByText('Left Wall')).toBeInTheDocument()
    expect(screen.getByText('Right Wall')).toBeInTheDocument()
    expect(screen.getByText('Base Ring')).toBeInTheDocument()
    expect(screen.getByText('Pillars')).toBeInTheDocument()
    expect(screen.getByText('Snap Beams')).toBeInTheDocument()
  })

  it('disables child checkboxes when parent is unchecked', () => {
    renderControls({
      params: {
        size: 20, thick: 2.5, rod_D: 3,
        show_base: true, show_walls: false, show_mech: true, show_letter: true,
        show_wall_left: true, show_wall_right: true,
        show_mech_base_ring: true, show_mech_pillars: true, show_mech_snap_beams: true,
      },
    })

    // Toggle to advanced mode
    const advancedBtn = screen.getByText('Advanced')
    fireEvent.click(advancedBtn)

    // Left Wall and Right Wall should be disabled since show_walls is false
    const leftWallCheckbox = screen.getByRole('checkbox', { name: 'Left Wall' })
    expect(leftWallCheckbox).toBeDisabled()
    const rightWallCheckbox = screen.getByRole('checkbox', { name: 'Right Wall' })
    expect(rightWallCheckbox).toBeDisabled()
  })

  it('sliders are labelled via aria-labelledby pointing to the parameter label', () => {
    renderControls()
    // aria-labelledby on Slider Root is forwarded to the Thumb (role="slider") by Radix
    expect(screen.getByLabelText('Size (mm)')).toBeInTheDocument()
    expect(screen.getByLabelText('Thickness (mm)')).toBeInTheDocument()
    expect(screen.getByLabelText('Rod Diameter (mm)')).toBeInTheDocument()
  })

  it('value displays have descriptive aria-label', () => {
    renderControls()
    const valueDisplay = screen.getByLabelText(/Size \(mm\): 20\. (Click to edit|Clic para editar)/)
    expect(valueDisplay).toBeInTheDocument()
    expect(valueDisplay).toHaveAttribute('role', 'button')
    expect(valueDisplay).toHaveAttribute('tabIndex', '0')
  })

  it('renders default star indicators on slider tracks', () => {
    renderControls()
    // Stars should always be present as default position indicators, not conditional on value
    expect(screen.getByTestId('default-star-size')).toBeInTheDocument()
    expect(screen.getByTestId('default-star-thick')).toBeInTheDocument()
    expect(screen.getByTestId('default-star-rod_D')).toBeInTheDocument()
  })

  it('default star remains when value differs from default', () => {
    renderControls({ params: {
      size: 25, thick: 2.5, rod_D: 3,
      show_base: true, show_walls: true, show_mech: true, show_letter: true,
      show_wall_left: true, show_wall_right: true,
      show_mech_base_ring: true, show_mech_pillars: true, show_mech_snap_beams: true,
    }})
    // Star should still be present even though size (25) != default (20)
    expect(screen.getByTestId('default-star-size')).toBeInTheDocument()
  })

  it('checkboxes use boolean checked to avoid controlled/uncontrolled warning', () => {
    // Pass undefined for a checkbox param — should render without error
    renderControls({
      params: {
        size: 20, thick: 2.5, rod_D: 3,
        show_base: undefined, show_walls: true, show_mech: true, show_letter: true,
        show_wall_left: true, show_wall_right: true,
        show_mech_base_ring: true, show_mech_pillars: true, show_mech_snap_beams: true,
      },
    })
    // Base checkbox should render as unchecked (!!undefined === false), not crash
    const baseCheckbox = screen.getByRole('checkbox', { name: 'Base' })
    expect(baseCheckbox).toBeInTheDocument()
    expect(baseCheckbox).toHaveAttribute('aria-checked', 'false')
  })
})
