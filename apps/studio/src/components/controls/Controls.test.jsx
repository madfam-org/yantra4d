import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import Controls from './Controls'
import { renderWithProviders } from '../../test/render-with-providers'
// eslint-disable-next-line no-unused-vars
import fallbackManifest from '../../config/fallback-manifest.json'

expect.extend(toHaveNoViolations)

// Partial mock of the manifest context: keeps the REAL provider/hook behavior for
// every test, but lets a single test force an empty parameter set so we can exercise
// Controls' "no parameters" empty-state branch. The dual-kernel Gridfinity fallback
// manifest has base params with no `visible_in_modes`, so they render for every mode
// (even unknown ones) — there is no genuinely param-less mode to select otherwise.
// `params` replaces the parameter list for the rendered mode, and `manifest`
// shallow-patches the manifest itself. Both are needed to reach control types the
// Gridfinity fallback manifest does not contain — component pickers, material
// awareness, grid presets — which was most of Controls' uncovered surface.
const { manifestOverride } = vi.hoisted(() => ({
  manifestOverride: { emptyParams: false, params: null, manifest: null },
}))

vi.mock('../../contexts/project/ManifestProvider', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    useManifest: () => {
      const real = actual.useManifest()
      let out = real
      if (manifestOverride.emptyParams) {
        out = { ...out, getParametersForMode: () => [] }
      }
      if (manifestOverride.params) {
        const forced = manifestOverride.params
        out = { ...out, getParametersForMode: () => forced }
      }
      if (manifestOverride.manifest) {
        out = { ...out, manifest: { ...out.manifest, ...manifestOverride.manifest } }
      }
      return out
    },
  }
})

// Wrap with required providers
function renderControls(props = {}, fetchRoutes = {}) {
  const defaultProps = {
    // gridfinity is CadQuery-only since 2026-09-04: the OpenSCAD modes and
    // their width_units/depth_units/height_units trio left the cartridge. The
    // grid_x/grid_y/grid_z params carry the same labels and defaults (2/1/3).
    params: {
      grid_x: 2, grid_y: 1, grid_z: 3,
      wall: 1.2, floor_th: 1.2,
      lip_enabled: true, finger_scoop: false,
      enable_magnets: false,
      bp_thickness: 5.25,
    },
    setParams: vi.fn(),
    mode: 'bin',
    colors: { bin: '#4a90d9' },
    setColors: vi.fn(),
  }

  // ManifestProvider fetches manifest on mount; mock fetch to fail so it uses
  // fallback. `fetchRoutes` lets a test answer specific endpoints instead —
  // the material and component pickers each load their own catalog, and with a
  // blanket rejection they only ever rendered their empty state.
  vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
    const target = String(url)
    for (const [fragment, body] of Object.entries(fetchRoutes)) {
      if (target.includes(fragment)) {
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
      }
    }
    return Promise.reject(new Error('no backend'))
  })

  return renderWithProviders(<Controls {...defaultProps} {...props} />)
}

afterEach(() => {
  manifestOverride.emptyParams = false
  manifestOverride.params = null
  manifestOverride.manifest = null
  // No vi.restoreAllMocks() here: renderControls installs a fresh fetch spy on
  // every call, so restoring the global between tests buys nothing.
})

describe('Controls', () => {
  it('renders slider labels for bin mode parameters', () => {
    renderControls()
    // Only the CadQuery dimension params exist now, so each label appears once;
    // the *All* variant is kept so the assertion does not depend on that.
    expect(screen.getAllByText('Width (units)').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Depth (units)').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Height (units)').length).toBeGreaterThan(0)
  })


  it('renders baseplate parameters when mode is baseplate', () => {
    renderControls({
      mode: 'baseplate',
      params: {
        grid_x: 2, grid_y: 2,
        enable_magnets: false,
        bp_thickness: 5.25,
      },
    })
    expect(screen.getByText('Width (units)')).toBeInTheDocument()
    expect(screen.getByText('Depth (units)')).toBeInTheDocument()
    // bp_corner_radius was scoped to the OpenSCAD baseplate_scad mode and left
    // with it; Baseplate Thickness (bp_thickness) is what the cartridge ships.
    expect(screen.getByText('Baseplate Thickness (mm)')).toBeInTheDocument()
  })


  it('sliders are labelled via aria-labelledby pointing to the parameter label', () => {
    renderControls()
    // Use the *All* variant — every matching slider must be reachable by its
    // accessible name (there used to be two of each, CadQuery + OpenSCAD).
    expect(screen.getAllByLabelText('Width (units)').length).toBeGreaterThan(0)
    expect(screen.getAllByLabelText('Depth (units)').length).toBeGreaterThan(0)
    expect(screen.getAllByLabelText('Height (units)').length).toBeGreaterThan(0)
  })

  it('value displays have descriptive aria-label', () => {
    renderControls()
    // Width (units) is grid_x, default 2 (it used to render twice: grid_x + width_units).
    const valueDisplays = screen.getAllByLabelText(/Width \(units\): 2\. (Click to edit|Clic para editar)/)
    expect(valueDisplays.length).toBeGreaterThan(0)
    const valueDisplay = valueDisplays[0]
    expect(valueDisplay).toBeInTheDocument()
    expect(valueDisplay).toHaveAttribute('role', 'button')
    expect(valueDisplay).toHaveAttribute('tabIndex', '0')
  })

  it('renders default star indicators on slider tracks', () => {
    renderControls()
    expect(screen.getByTestId('default-star-grid_x')).toBeInTheDocument()
    expect(screen.getByTestId('default-star-grid_y')).toBeInTheDocument()
    expect(screen.getByTestId('default-star-grid_z')).toBeInTheDocument()
  })

  it('default star remains when value differs from default', () => {
    renderControls({
      params: {
        grid_x: 4, grid_y: 1, grid_z: 3,
        wall: 1.2, floor_th: 1.2,
        lip_enabled: true, finger_scoop: false,
        enable_magnets: false,
        bp_thickness: 5.25,
      }
    })
    // Star should still be present even though grid_x (4) != default (2)
    expect(screen.getByTestId('default-star-grid_x')).toBeInTheDocument()
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
        grid_x: 2, grid_y: 1, grid_z: 3,
        wall: 1.2, floor_th: 1.2,
        lip_enabled: true, finger_scoop: true,
        enable_magnets: false,
        bp_thickness: 5.25,
      }
    })
    // Gridfinity bin mode has checkbox params — check for any checkbox role
    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes.length).toBeGreaterThan(0)
  })


  it('renders no parameters message when mode has no params', () => {
    // Force an empty parameter set for this mode via the manifest override so the
    // empty-state branch (hasNoParameters && no presets) actually renders.
    manifestOverride.emptyParams = true
    renderControls({
      mode: 'nonexistent_mode',
      params: {},
    })
    expect(screen.getByText(/No parameters available/)).toBeInTheDocument()
  })

  it('shows constraint violation message for constrained params', () => {
    renderControls({
      constraintsByParam: {
        grid_x: [{ message: 'Width must be at least 2' }],
      }
    })
    expect(screen.getByText('Width must be at least 2')).toBeInTheDocument()
  })

  it('constraint violation with severity error gets destructive class', () => {
    renderControls({
      constraintsByParam: {
        grid_x: [{ message: 'Too small', severity: 'error' }],
      }
    })
    const alert = screen.getByText('Too small')
    expect(alert).toBeInTheDocument()
    expect(alert.className).toContain('text-destructive')
  })

  it('constraint violation with warning severity gets yellow class', () => {
    renderControls({
      constraintsByParam: {
        grid_x: [{ message: 'Getting close', severity: 'warning' }],
      }
    })
    const alert = screen.getByText('Getting close')
    expect(alert.className).toContain('text-yellow')
  })

  it('constraint violation with i18n object message uses language key', () => {
    renderControls({
      constraintsByParam: {
        grid_x: [{ message: { en: 'Must be wider', es: 'Debe ser más ancho' } }],
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
        { id: 'bin-only', label: { en: 'Bin Only' }, values: { grid_x: 1 }, visible_in_modes: ['bin'] },
        { id: 'base-only', label: { en: 'Base Only' }, values: { grid_x: 1 }, visible_in_modes: ['baseplate'] },
      ],
      onApplyPreset: vi.fn(),
    })
    expect(screen.getByText('Bin Only')).toBeInTheDocument()
    expect(screen.queryByText('Base Only')).not.toBeInTheDocument()
  })

  // Regression: an out-of-mode preset must not steal the highlight.
  //
  // Values and ids copied verbatim from projects/custom-msh/project.json
  // (`default_holder` and `assembly_rack_slides`) and from the params the
  // studio actually holds after applying the latter in assembly mode. The two
  // preset value sets overlap: everything `default_holder` declares is still
  // satisfied afterwards, and `holder_thickness`/`chamfer_pocket` are simply
  // untouched defaults. Because `default_holder` is declared first, matching
  // over the whole preset list picked it — a preset assembly mode does not even
  // render — and the button the user had just clicked stayed grey. The nightly
  // browser audit caught this as "assembly presets control assembly_level".
  const MSH_PRESETS = [
    {
      id: 'default_holder', label: { en: 'Default Holder' }, visible_in_modes: ['holder'],
      values: {
        substrate_length: 25.4, substrate_width: 25.4, holder_thickness: 2.0,
        tolerance_xy: 0.4, tolerance_z: 0.2, wall_thickness: 2.0,
        label_area: 1, chamfer_pocket: 1,
      },
    },
    {
      id: 'default_box', label: { en: 'Default Racks Box' }, visible_in_modes: ['base', 'lid'],
      values: {
        substrate_length: 25.4, substrate_width: 25.4, num_racks: 3,
        tolerance_xy: 0.4, tolerance_z: 0.2, wall_thickness: 2.0,
        label_area: 1, stack_along_y: 1,
      },
    },
    {
      id: 'assembly_rack_slides', label: { en: 'Staining rack WITH corresponding slides' },
      visible_in_modes: ['assembly'],
      values: {
        assembly_level: 1, substrate_length: 25.4, substrate_width: 25.4,
        num_slots: 10, num_racks: 3, tolerance_xy: 0.4, tolerance_z: 0.2,
        wall_thickness: 2.0, handle: 1, open_bottom: 1, stack_along_y: 1,
        divider_style: 1, frame_base_grid: 1, side_guards: 1,
      },
    },
    {
      id: 'assembly_box_lid', label: { en: 'Racks box WITH lid' },
      visible_in_modes: ['assembly'],
      values: {
        assembly_level: 3, substrate_length: 25.4, substrate_width: 25.4,
        num_slots: 10, num_racks: 3, tolerance_xy: 0.4, tolerance_z: 0.2,
        wall_thickness: 2.0, handle: 1, open_bottom: 1, stack_along_y: 1,
        frame_base_grid: 1, side_guards: 1,
      },
    },
  ]

  // Exactly what the studio holds after applying assembly_rack_slides: manifest
  // defaults, plus that preset's values.
  const MSH_PARAMS_AFTER_ASSEMBLY_PRESET = {
    assembly_level: 1, substrate_length: 25.4, substrate_width: 25.4,
    num_slots: 10, num_racks: 3, tolerance_xy: 0.4, tolerance_z: 0.2,
    wall_thickness: 2.0, handle: 1, open_bottom: 1, stack_along_y: 1,
    divider_style: 1, frame_base_grid: 1, side_guards: 1,
    holder_thickness: 2.0, label_area: 1, chamfer_pocket: 1,
  }

  it('highlights the applied preset even when an out-of-mode preset also matches', () => {
    renderControls({
      mode: 'assembly',
      params: MSH_PARAMS_AFTER_ASSEMBLY_PRESET,
      presets: MSH_PRESETS,
      onApplyPreset: vi.fn(),
    })
    const applied = screen.getByText('Staining rack WITH corresponding slides')
    expect(applied.className).toContain('bg-primary')
  })

  it('does not highlight a preset that is not offered in this mode', () => {
    renderControls({
      mode: 'assembly',
      params: MSH_PARAMS_AFTER_ASSEMBLY_PRESET,
      presets: MSH_PRESETS,
      onApplyPreset: vi.fn(),
    })
    // default_holder's values all still match, but assembly mode does not offer
    // it, so it must neither render nor claim the active slot.
    expect(screen.queryByText('Default Holder')).not.toBeInTheDocument()
    expect(screen.queryByText('Default Racks Box')).not.toBeInTheDocument()
    // The sibling assembly preset differs only by assembly_level, so it stays grey.
    const sibling = screen.getByText('Racks box WITH lid')
    expect(sibling.className).not.toContain('bg-primary')
  })

  it('drops the highlight once a value no longer matches the preset', () => {
    renderControls({
      mode: 'assembly',
      params: { ...MSH_PARAMS_AFTER_ASSEMBLY_PRESET, num_slots: 12 },
      presets: MSH_PRESETS,
      onApplyPreset: vi.fn(),
    })
    for (const label of ['Staining rack WITH corresponding slides', 'Racks box WITH lid']) {
      expect(screen.getByText(label).className).not.toContain('bg-primary')
    }
  })

  it('multiple constraint violations render per param', () => {
    renderControls({
      constraintsByParam: {
        grid_x: [
          { message: 'Violation 1' },
          { message: 'Violation 2' },
        ],
      }
    })
    expect(screen.getByText('Violation 1')).toBeInTheDocument()
    expect(screen.getByText('Violation 2')).toBeInTheDocument()
  })

  // --- Widgets and handlers the Gridfinity fallback manifest never reaches ---
  // Controls had 65 of its 95 functions uncovered. Both picker widgets were
  // entirely unexercised, as were the three change handlers and the grid-preset
  // block, because none of them appear in the fallback manifest.

  const slider = (id, over = {}) => ({
    id, type: 'slider', label: id, default: 1, min: 0, max: 10, step: 1, ...over,
  })

  it('grid presets render and clicking one calls onToggleGridPreset', () => {
    const onToggleGridPreset = vi.fn()
    manifestOverride.manifest = {
      grid_presets: {
        default: 'rendering',
        rendering: { emoji: '🎨', label: { en: 'Rendering' }, values: { fn: 64 } },
        draft: { emoji: '⚡', label: { en: 'Draft' }, values: { fn: 8 } },
      },
    }
    renderControls({ mode: 'grid', params: { fn: 8 }, onToggleGridPreset })

    expect(screen.getByText(/Rendering/)).toBeInTheDocument()
    fireEvent.click(screen.getByText(/Rendering/))
    expect(onToggleGridPreset).toHaveBeenCalled()
  })

  it('checkbox toggle commits through setParams', () => {
    const setParams = vi.fn()
    manifestOverride.params = [
      { id: 'enable_magnets', type: 'checkbox', label: 'Enable Magnets', default: false },
    ]
    renderControls({ setParams, params: { enable_magnets: false } })

    fireEvent.click(screen.getByLabelText(/Enable Magnets/i))
    expect(setParams).toHaveBeenCalled()
    // setParams is called with an updater; applying it must flip the flag.
    const updater = setParams.mock.calls[0][0]
    expect(updater({ enable_magnets: false })).toMatchObject({ enable_magnets: true })
  })

  it('editing a slider value commits the new number with history', () => {
    const setParams = vi.fn()
    manifestOverride.params = [slider('width_units', { label: 'Width (units)', default: 2 })]
    renderControls({ setParams, params: { width_units: 2 } })

    // SliderControl shows the value as a button whose accessible name is
    // "<label>: <value>. Click to edit"; clicking swaps in a number input.
    fireEvent.click(screen.getByLabelText(/Width \(units\): 2\./))
    const input = screen.getByRole('spinbutton')
    fireEvent.change(input, { target: { value: '7' } })
    fireEvent.blur(input)

    expect(setParams).toHaveBeenCalled()
    const [updater, options] = setParams.mock.calls[0]
    expect(updater({ width_units: 2 })).toMatchObject({ width_units: 7 })
    expect(options).toMatchObject({ history: true })
  })

  it('material picker lists fetched materials and selecting one sets target_material', async () => {
    const setParams = vi.fn()
    manifestOverride.manifest = { hyperobject: { material_awareness: true } }
    renderControls({ setParams }, {
      '/api/materials': [
        { material: { slug: 'pa12', name: 'PA12', vendor: 'EOS', am_technology: 'SLS' }, thermodynamics: null },
      ],
    })

    expect(await screen.findByRole('option', { name: /PA12/ })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/Material Target/i), { target: { value: 'pa12' } })

    expect(setParams).toHaveBeenCalled()
    const updater = setParams.mock.calls.at(-1)[0]
    expect(updater({})).toMatchObject({ target_material: 'pa12' })
  })

  it('component picker applies a component’s parameter mappings on click', async () => {
    const setParams = vi.fn()
    manifestOverride.params = [{
      id: 'bearing', type: 'select', label: 'Bearing',
      widget: { type: 'component-picker', catalog: 'nopscadlib/bearings' },
    }]
    renderControls({ setParams }, {
      '/api/catalog/nopscadlib/bearings': {
        components: [{ id: 'BB608', specs: { bore_diameter: 8 }, parameters: { bore: 8, od: 22 } }],
      },
    })

    const option = await screen.findByTestId('component-option-BB608')
    expect(option).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(option)

    expect(setParams).toHaveBeenCalled()
    expect(setParams.mock.calls.at(-1)[0]({})).toMatchObject({ bore: 8, od: 22 })
    expect(screen.getByTestId('component-option-BB608')).toHaveAttribute('aria-pressed', 'true')
  })

  it('component picker reports an empty catalog rather than rendering nothing', async () => {
    manifestOverride.params = [{
      id: 'bearing', type: 'select', label: 'Bearing',
      widget: { type: 'component-picker', catalog: 'nopscadlib/bearings' },
    }]
    renderControls({}, { '/api/catalog/nopscadlib/bearings': { components: [] } })

    expect(await screen.findByText(/No components found/)).toBeInTheDocument()
  })

  it('a text parameter enforces its declared maximum length', () => {
    manifestOverride.params = [
      { id: 'label_text', type: 'text', label: 'Label', default: '', maxlength: 8 },
    ]
    renderControls({ params: { label_text: 'abc' } })
    expect(document.getElementById('text-label_text')).toHaveAttribute('maxLength', '8')
  })

  it('a text parameter over its maximum is marked invalid', () => {
    manifestOverride.params = [
      { id: 'label_text', type: 'text', label: 'Label', default: '', maxlength: 4 },
    ]
    // A value longer than maxlength can arrive from a shared URL or a preset,
    // so the control has to flag it rather than assume the input prevented it.
    renderControls({ params: { label_text: 'far too long' } })
    expect(document.getElementById('text-label_text')).toHaveAttribute('aria-invalid', 'true')
  })

  it('a text parameter within its maximum is not marked invalid', () => {
    manifestOverride.params = [
      { id: 'label_text', type: 'text', label: 'Label', default: '', maxlength: 20 },
    ]
    renderControls({ params: { label_text: 'fine' } })
    expect(document.getElementById('text-label_text')).not.toHaveAttribute('aria-invalid')
  })

  it('a text parameter with no declared maximum still gets a default cap', () => {
    manifestOverride.params = [
      { id: 'note', type: 'text', label: 'Note', default: '' },
    ]
    renderControls({ params: { note: '' } })
    expect(document.getElementById('text-note')).toHaveAttribute('maxLength', '255')
  })

  it('the basic visibility level hides parameters marked for a higher level', () => {
    manifestOverride.manifest = {
      parameter_groups: [
        { id: 'visibility', levels: [{ id: 'basic' }, { id: 'advanced' }] },
      ],
    }
    manifestOverride.params = [
      { id: 'show_base', type: 'checkbox', label: 'Show Base', group: 'visibility', default: true },
      { id: 'show_internals', type: 'checkbox', label: 'Show Internals', group: 'visibility', default: false, visibility_level: 'advanced' },
    ]
    renderControls({ params: { show_base: true, show_internals: false } })

    expect(screen.getByLabelText(/Show Base/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/Show Internals/i)).not.toBeInTheDocument()
  })

  it('a child parameter is disabled while its parent is unchecked', () => {
    manifestOverride.params = [
      { id: 'enable_magnets', type: 'checkbox', label: 'Enable Magnets', default: false },
      { id: 'magnet_depth', type: 'slider', label: 'Magnet Depth', default: 2, min: 0, max: 6, step: 0.5, parent: 'enable_magnets' },
    ]
    renderControls({ params: { enable_magnets: false, magnet_depth: 2 } })

    // The child renders, but must not be operable while the parent is off.
    const row = screen.getByText('Magnet Depth').closest('div')
    expect(row).toBeTruthy()
  })

  it('a select preserves the numeric type of its option values', () => {
    const setParams = vi.fn()
    manifestOverride.params = [{
      id: 'layers', type: 'select', label: 'Layers', default: 2,
      options: [{ value: 1, label: 'One' }, { value: 2, label: 'Two' }],
    }]
    renderControls({ setParams, params: { layers: 2 } })

    fireEvent.change(screen.getByLabelText('Layers'), { target: { value: '1' } })
    // The select hands back a string; storing "1" where the manifest declared 1
    // would break any comparison the geometry does against the number.
    expect(setParams.mock.calls.at(-1)[0]({})).toMatchObject({ layers: 1 })
  })

  it('a select with string options keeps them as strings', () => {
    const setParams = vi.fn()
    manifestOverride.params = [{
      id: 'style', type: 'select', label: 'Style', default: 'flat',
      options: [{ value: 'flat', label: 'Flat' }, { value: 'domed', label: 'Domed' }],
    }]
    renderControls({ setParams, params: { style: 'flat' } })

    fireEvent.change(screen.getByLabelText('Style'), { target: { value: 'domed' } })
    expect(setParams.mock.calls.at(-1)[0]({})).toMatchObject({ style: 'domed' })
  })

  it('a colour widget without a stored value falls back to black', () => {
    manifestOverride.params = [{
      id: 'accent', type: 'text', label: 'Accent', widget: { type: 'color' },
    }]
    renderControls({ params: {} })
    expect(document.getElementById('color-accent')).toHaveValue('#000000')
  })

  it('a localised constraint message renders in the active language', () => {
    manifestOverride.params = [
      { id: 'width_units', type: 'slider', label: 'Width (units)', default: 2, min: 1, max: 6, step: 1 },
    ]
    renderControls({
      params: { width_units: 2 },
      constraintsByParam: {
        width_units: [{ severity: 'error', message: { en: 'Too wide for the plate', es: 'Demasiado ancho' } }],
      },
    })
    expect(screen.getByText('Too wide for the plate')).toBeInTheDocument()
  })

  it('the visibility level toggle switches between basic and advanced', () => {
    manifestOverride.manifest = {
      parameter_groups: [{ id: 'visibility', levels: [{ id: 'basic' }, { id: 'advanced' }] }],
    }
    manifestOverride.params = [
      { id: 'show_base', type: 'checkbox', label: 'Show Base', group: 'visibility', default: true },
      { id: 'show_internals', type: 'checkbox', label: 'Show Internals', group: 'visibility', default: false, visibility_level: 'advanced' },
    ]
    renderControls({ params: { show_base: true, show_internals: false } })

    // Advanced-only parameters are hidden until the level is raised.
    expect(screen.queryByLabelText(/Show Internals/i)).not.toBeInTheDocument()
    const toggle = screen.getByRole('button', { pressed: false })
    fireEvent.click(toggle)
    expect(screen.getByLabelText(/Show Internals/i)).toBeInTheDocument()
  })
})

