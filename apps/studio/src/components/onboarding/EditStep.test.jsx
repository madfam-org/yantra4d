import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import EditStep from './EditStep'

const baseManifest = {
  project: { name: 'Test Project', slug: 'test-project' },
  modes: [
    { id: 'default', label: { en: 'Default' }, scad_file: 'main.scad' },
    { id: 'alt', label: 'Alt Mode', scad_file: 'alt.scad' },
  ],
  parameters: [
    { id: 'width', type: 'slider', default: 10, min: 1, max: 100 },
    { id: 'label_text', type: 'text', default: 'hello' },
  ],
  parts: [
    { id: 'body', default_color: '#ff0000' },
  ],
}

const t = (key) => {
  const map = {
    'onboard.edit_title': 'Edit Manifest',
    'onboard.structured_view': 'Structured View',
    'onboard.raw_json': 'Raw JSON',
    'onboard.manifest_json': 'Manifest JSON',
    'onboard.project_name': 'Project Name',
    'onboard.modes_label': 'Modes',
    'onboard.params_label': 'Parameters',
    'onboard.parts_label': 'Parts',
    'onboard.back': 'Back',
    'onboard.review_save': 'Review & Save',
  }
  return map[key] || key
}

function renderEditStep(overrides = {}) {
  const props = {
    manifest: baseManifest,
    setManifest: vi.fn(),
    onBack: vi.fn(),
    onNext: vi.fn(),
    t,
    ...overrides,
  }
  return { ...render(<EditStep {...props} />), ...props }
}

describe('EditStep', () => {
  it('renders title and toggle button', () => {
    renderEditStep()
    expect(screen.getByText('Edit Manifest')).toBeInTheDocument()
    expect(screen.getByText('Raw JSON')).toBeInTheDocument()
  })

  it('renders structured view by default with project name input', () => {
    renderEditStep()
    expect(screen.getByDisplayValue('Test Project')).toBeInTheDocument()
    expect(screen.getByText('Project Name')).toBeInTheDocument()
  })

  it('renders mode cards with IDs and labels', () => {
    renderEditStep()
    expect(screen.getByDisplayValue('default')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Default')).toBeInTheDocument()
    expect(screen.getByText('main.scad')).toBeInTheDocument()
  })

  it('renders parameter table with correct columns', () => {
    renderEditStep()
    expect(screen.getByText('ID')).toBeInTheDocument()
    expect(screen.getByText('Type')).toBeInTheDocument()
    expect(screen.getByText('Default')).toBeInTheDocument()
    expect(screen.getByText('Min')).toBeInTheDocument()
    expect(screen.getByText('Max')).toBeInTheDocument()
  })

  it('renders parameter rows', () => {
    renderEditStep()
    expect(screen.getByText('width')).toBeInTheDocument()
    expect(screen.getByText('slider')).toBeInTheDocument()
    expect(screen.getByText('label_text')).toBeInTheDocument()
    expect(screen.getByText('text')).toBeInTheDocument()
  })

  it('renders parts section with color pickers', () => {
    renderEditStep()
    expect(screen.getByText('Parts')).toBeInTheDocument()
    expect(screen.getByText('body')).toBeInTheDocument()
    expect(screen.getByDisplayValue('#ff0000')).toBeInTheDocument()
  })

  it('toggles to raw JSON view', () => {
    renderEditStep()
    fireEvent.click(screen.getByText('Raw JSON'))
    expect(screen.getByText('Manifest JSON')).toBeInTheDocument()
    // Should show textarea with JSON
    const textarea = screen.getByRole('textbox')
    expect(textarea.value).toContain('test-project')
  })

  it('toggles back to structured view', () => {
    renderEditStep()
    fireEvent.click(screen.getByText('Raw JSON'))
    expect(screen.getByText('Structured View')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Structured View'))
    expect(screen.getByText('Project Name')).toBeInTheDocument()
  })

  it('shows error for invalid JSON in raw mode', () => {
    renderEditStep()
    fireEvent.click(screen.getByText('Raw JSON'))
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: '{invalid json' } })
    expect(screen.getByText(/Invalid JSON/)).toBeInTheDocument()
  })

  it('valid JSON in raw mode calls setManifest', () => {
    const setManifest = vi.fn()
    renderEditStep({ setManifest })
    fireEvent.click(screen.getByText('Raw JSON'))
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: '{"project":{"name":"Updated"}}' } })
    expect(setManifest).toHaveBeenCalledWith({ project: { name: 'Updated' } })
  })

  it('editing project name calls setManifest', () => {
    const setManifest = vi.fn()
    renderEditStep({ setManifest })
    const nameInput = screen.getByDisplayValue('Test Project')
    fireEvent.change(nameInput, { target: { value: 'New Name' } })
    expect(setManifest).toHaveBeenCalled()
  })

  it('back button calls onBack', () => {
    const onBack = vi.fn()
    renderEditStep({ onBack })
    fireEvent.click(screen.getByText('Back'))
    expect(onBack).toHaveBeenCalledOnce()
  })

  it('next button calls onNext', () => {
    const onNext = vi.fn()
    renderEditStep({ onNext })
    fireEvent.click(screen.getByText('Review & Save'))
    expect(onNext).toHaveBeenCalledOnce()
  })

  it('does not render parts section when parts is empty', () => {
    renderEditStep({ manifest: { ...baseManifest, parts: [] } })
    expect(screen.queryByText('Parts')).not.toBeInTheDocument()
  })

  it('handles mode label as string', () => {
    renderEditStep()
    // Alt Mode has label as a plain string, not an object
    expect(screen.getByDisplayValue('Alt Mode')).toBeInTheDocument()
  })

  it('editing mode ID calls setManifest', () => {
    const setManifest = vi.fn()
    renderEditStep({ setManifest })
    const modeIdInput = screen.getByDisplayValue('default')
    fireEvent.change(modeIdInput, { target: { value: 'main' } })
    expect(setManifest).toHaveBeenCalled()
  })

  it('editing parameter default calls setManifest', () => {
    const setManifest = vi.fn()
    renderEditStep({ setManifest })
    const defaultInputs = screen.getAllByRole('spinbutton')
    // First spinbutton should be the slider default (10)
    const widthDefault = defaultInputs.find(i => i.value === '10')
    if (widthDefault) {
      fireEvent.change(widthDefault, { target: { value: '20' } })
      expect(setManifest).toHaveBeenCalled()
    }
  })

  it('textarea has aria-invalid when JSON error exists', () => {
    renderEditStep()
    fireEvent.click(screen.getByText('Raw JSON'))
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: 'bad' } })
    expect(textarea).toHaveAttribute('aria-invalid', 'true')
  })

  // --- Structured editors ---------------------------------------------------
  // The raw JSON path was covered; the structured editors below it — mode id and
  // label, parameter bounds, part colours — were not, so none of their onChange
  // handlers ran.

  /** Apply the updater setManifest was called with, to see the edit it encodes. */
  const applyLastUpdate = (setManifest, prev) => {
    const updater = setManifest.mock.calls.at(-1)[0]
    return typeof updater === 'function' ? updater(prev) : updater
  }

  it('editing a mode id rewrites that mode in place', () => {
    const setManifest = vi.fn()
    renderEditStep({ setManifest })
    fireEvent.change(screen.getByDisplayValue('default'), { target: { value: 'primary' } })
    const next = applyLastUpdate(setManifest, baseManifest)
    expect(next.modes[0].id).toBe('primary')
    expect(next.modes[1].id).toBe('alt') // siblings untouched
  })

  it('editing a mode label replaces the locale map with the typed string', () => {
    const setManifest = vi.fn()
    renderEditStep({ setManifest })
    // The first mode's label is { en: 'Default' }; the input shows the en value.
    fireEvent.change(screen.getByDisplayValue('Default'), { target: { value: 'Primary' } })
    expect(applyLastUpdate(setManifest, baseManifest).modes[0].label).toBe('Primary')
  })

  it('editing a slider bound stores a number, not the raw string', () => {
    const setManifest = vi.fn()
    renderEditStep({ setManifest })
    fireEvent.change(screen.getByDisplayValue('100'), { target: { value: '250' } })
    expect(applyLastUpdate(setManifest, baseManifest).parameters[0].max).toBe(250)
  })

  it('a non-numeric bound falls back to zero rather than NaN', () => {
    const setManifest = vi.fn()
    renderEditStep({ setManifest })
    fireEvent.change(screen.getByDisplayValue('100'), { target: { value: 'abc' } })
    expect(applyLastUpdate(setManifest, baseManifest).parameters[0].max).toBe(0)
  })

  it('choosing a part colour updates that part', () => {
    const setManifest = vi.fn()
    renderEditStep({ setManifest })
    fireEvent.change(screen.getByDisplayValue('#ff0000'), { target: { value: '#00ff00' } })
    expect(applyLastUpdate(setManifest, baseManifest).parts[0].default_color).toBe('#00ff00')
  })
})

