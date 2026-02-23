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

  it('has no a11y violations', { timeout: 30000 }, async () => {
    const { container } = renderControls()
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  it('renders checkbox controls for boolean parameters', () => {
    renderControls({
      params: {
        width_units: 2, depth_units: 1, height_units: 3,
        cup_wall_thickness: 0, cup_floor_thickness: 0.7,
        vertical_chambers: 1, horizontal_chambers: 1,
        fingerslide_enabled: true, label_enabled: false,
        enable_magnets: false, enable_screws: false,
        fn: 0,
      }
    })
    // Gridfinity cup mode has checkbox params — check for any checkbox role
    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes.length).toBeGreaterThan(0)
  })

  it('renders wireframe toggle when setWireframe is provided', () => {
    const setWireframe = vi.fn()
    renderControls({ wireframe: false, setWireframe })
    expect(screen.getByText('Wireframe')).toBeInTheDocument()
  })

  it('renders bounding box toggle when setBoundingBox is provided', () => {
    const setBoundingBox = vi.fn()
    renderControls({ boundingBox: false, setBoundingBox })
    expect(screen.getByText('Bounding Box')).toBeInTheDocument()
  })

  it('renders no parameters message when mode has no params', () => {
    // Use a mode that has no params by providing an unknown mode
    renderControls({
      mode: 'nonexistent_mode',
      params: {},
    })
    expect(screen.getByText(/No parameters available/)).toBeInTheDocument()
  })

  it('shows constraint violation message for constrained params', () => {
    renderControls({
      constraintsByParam: {
        width_units: [{ message: 'Width must be at least 2' }],
      }
    })
    expect(screen.getByText('Width must be at least 2')).toBeInTheDocument()
  })

  it('constraint violation with severity error gets destructive class', () => {
    renderControls({
      constraintsByParam: {
        width_units: [{ message: 'Too small', severity: 'error' }],
      }
    })
    const alert = screen.getByText('Too small')
    expect(alert).toBeInTheDocument()
    expect(alert.className).toContain('text-destructive')
  })

  it('constraint violation with warning severity gets yellow class', () => {
    renderControls({
      constraintsByParam: {
        width_units: [{ message: 'Getting close', severity: 'warning' }],
      }
    })
    const alert = screen.getByText('Getting close')
    expect(alert.className).toContain('text-yellow')
  })

  it('constraint violation with i18n object message uses language key', () => {
    renderControls({
      constraintsByParam: {
        width_units: [{ message: { en: 'Must be wider', es: 'Debe ser más ancho' } }],
      }
    })
    expect(screen.getByText('Must be wider')).toBeInTheDocument()
  })

  it('sliders are present for numeric parameters', () => {
    renderControls()
    const sliders = screen.getAllByRole('slider')
    expect(sliders.length).toBeGreaterThan(0)
  })

  it('checkbox change calls setParams', () => {
    const setParams = vi.fn()
    renderControls({
      setParams,
      params: {
        width_units: 2, depth_units: 1, height_units: 3,
        cup_wall_thickness: 0, cup_floor_thickness: 0.7,
        vertical_chambers: 1, horizontal_chambers: 1,
        fingerslide_enabled: false, label_enabled: false,
        enable_magnets: false, enable_screws: false,
        fn: 0,
      }
    })
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0])
    expect(setParams).toHaveBeenCalled()
  })

  it('renders presets when provided', () => {
    renderControls({
      presets: [
        { id: 'small', label: { en: 'Small' }, values: { width_units: 1, depth_units: 1, height_units: 1 } },
        { id: 'large', label: { en: 'Large' }, values: { width_units: 4, depth_units: 4, height_units: 4 } },
      ],
      onApplyPreset: vi.fn(),
    })
    expect(screen.getByText('Small')).toBeInTheDocument()
    expect(screen.getByText('Large')).toBeInTheDocument()
  })

  it('clicking a preset calls onApplyPreset', () => {
    const onApplyPreset = vi.fn()
    renderControls({
      presets: [
        { id: 'tiny', label: { en: 'Tiny' }, values: { width_units: 1 } },
      ],
      onApplyPreset,
    })
    fireEvent.click(screen.getByText('Tiny'))
    expect(onApplyPreset).toHaveBeenCalled()
  })

  it('active preset gets primary styling', () => {
    renderControls({
      params: {
        width_units: 1, depth_units: 1, height_units: 1,
        cup_wall_thickness: 0, cup_floor_thickness: 0.7,
        vertical_chambers: 1, horizontal_chambers: 1,
        fingerslide_enabled: false, label_enabled: false,
        enable_magnets: false, enable_screws: false,
        fn: 0,
      },
      presets: [
        { id: 'small', label: { en: 'Small' }, values: { width_units: 1, depth_units: 1, height_units: 1 } },
      ],
      onApplyPreset: vi.fn(),
    })
    const btn = screen.getByText('Small')
    expect(btn.className).toContain('bg-primary')
  })

  it('preset with visible_in_modes filters by current mode', () => {
    renderControls({
      presets: [
        { id: 'cup-only', label: { en: 'Cup Only' }, values: { width_units: 1 }, visible_in_modes: ['cup'] },
        { id: 'base-only', label: { en: 'Base Only' }, values: { width_units: 1 }, visible_in_modes: ['baseplate'] },
      ],
      onApplyPreset: vi.fn(),
    })
    expect(screen.getByText('Cup Only')).toBeInTheDocument()
    expect(screen.queryByText('Base Only')).not.toBeInTheDocument()
  })

  it('multiple constraint violations render per param', () => {
    renderControls({
      constraintsByParam: {
        width_units: [
          { message: 'Violation 1' },
          { message: 'Violation 2' },
        ],
      }
    })
    expect(screen.getByText('Violation 1')).toBeInTheDocument()
    expect(screen.getByText('Violation 2')).toBeInTheDocument()
  })
})
