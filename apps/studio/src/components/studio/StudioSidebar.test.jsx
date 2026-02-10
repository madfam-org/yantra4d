import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

vi.mock('../Controls', () => ({
  default: function MockControls() {
    return <div data-testid="controls" />
  },
}))
vi.mock('../export/ExportPanel', () => ({
  default: function MockExportPanel() {
    return <div data-testid="export-panel" />
  },
}))
vi.mock('../bom/BomPanel', () => ({
  default: function MockBomPanel() {
    return <div data-testid="bom-panel" />
  },
}))
vi.mock('../bom/AssemblyView', () => ({
  default: function MockAssemblyView() {
    return <div data-testid="assembly-view" />
  },
}))
vi.mock('../assembly-editor/AssemblyEditorPanel', () => ({
  default: function MockEditorPanel({ onClose }) {
    return <div data-testid="assembly-editor"><button onClick={onClose}>Close editor</button></div>
  },
}))

import StudioSidebar from './StudioSidebar'

const baseProps = {
  manifest: {
    modes: [
      { id: 'full', label: 'Full' },
      { id: 'plate', label: 'Plate' },
    ],
    assembly_steps: [],
  },
  mode: 'full',
  setMode: vi.fn(),
  getLabel: (m) => m.label,
  language: 'en',
  t: (key) => key,
  params: {},
  setParams: vi.fn(),
  colors: {},
  setColors: vi.fn(),
  wireframe: false,
  setWireframe: vi.fn(),
  presets: [],
  handleApplyPreset: vi.fn(),
  handleGridPresetToggle: vi.fn(),
  loading: false,
  parts: [],
  handleGenerate: vi.fn(),
  handleCancelGenerate: vi.fn(),
  handleVerify: vi.fn(),
  handleReset: vi.fn(),
  handleDownloadStl: vi.fn(),
  handleExportImage: vi.fn(),
  handleExportAllViews: vi.fn(),
  exportFormat: 'stl',
  setExportFormat: vi.fn(),
  constraintsByParam: {},
  constraintErrors: false,
  onAssemblyStepChange: vi.fn(),
  assemblyEditorOpen: false,
  setAssemblyEditorOpen: vi.fn(),
  viewerRef: { current: null },
  projectSlug: 'test',
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('StudioSidebar', () => {
  it('renders mode tabs for each mode in manifest', () => {
    render(<StudioSidebar {...baseProps} />)
    expect(screen.getAllByText('Full').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Plate').length).toBeGreaterThan(0)
  })

  it('renders generate button', () => {
    render(<StudioSidebar {...baseProps} />)
    expect(screen.getAllByText('btn.gen').length).toBeGreaterThan(0)
  })

  it('shows processing text when loading', () => {
    render(<StudioSidebar {...baseProps} loading={true} />)
    expect(screen.getAllByText('btn.proc').length).toBeGreaterThan(0)
  })

  it('shows cancel button when loading', () => {
    render(<StudioSidebar {...baseProps} loading={true} />)
    expect(screen.getAllByText('btn.cancel').length).toBeGreaterThan(0)
  })

  it('disables generate button when loading', () => {
    render(<StudioSidebar {...baseProps} loading={true} />)
    const genBtns = screen.getAllByText('btn.proc')
    genBtns.forEach(btn => {
      expect(btn.closest('button')).toBeDisabled()
    })
  })

  it('disables generate button when constraint errors', () => {
    render(<StudioSidebar {...baseProps} constraintErrors={true} />)
    const genBtns = screen.getAllByText('btn.gen')
    genBtns.forEach(btn => {
      expect(btn.closest('button')).toBeDisabled()
    })
  })

  it('disables verify button when no parts', () => {
    render(<StudioSidebar {...baseProps} parts={[]} />)
    const verifyBtns = screen.getAllByText('btn.verify')
    verifyBtns.forEach(btn => {
      expect(btn.closest('button')).toBeDisabled()
    })
  })

  it('enables verify button when parts available', () => {
    render(<StudioSidebar {...baseProps} parts={[{ id: 'body' }]} />)
    const verifyBtns = screen.getAllByText('btn.verify')
    verifyBtns.forEach(btn => {
      expect(btn.closest('button')).not.toBeDisabled()
    })
  })

  it('calls handleGenerate when clicking generate button', () => {
    render(<StudioSidebar {...baseProps} />)
    const genBtns = screen.getAllByText('btn.gen')
    fireEvent.click(genBtns[0].closest('button'))
    expect(baseProps.handleGenerate).toHaveBeenCalled()
  })

  it('calls handleReset when clicking reset button', () => {
    render(<StudioSidebar {...baseProps} />)
    const resetBtns = screen.getAllByText('btn.reset')
    fireEvent.click(resetBtns[0].closest('button'))
    expect(baseProps.handleReset).toHaveBeenCalled()
  })

  it('renders child panels: controls, export, bom, assembly', () => {
    render(<StudioSidebar {...baseProps} />)
    expect(screen.getAllByTestId('controls').length).toBeGreaterThan(0)
    expect(screen.getAllByTestId('export-panel').length).toBeGreaterThan(0)
    expect(screen.getAllByTestId('bom-panel').length).toBeGreaterThan(0)
    expect(screen.getAllByTestId('assembly-view').length).toBeGreaterThan(0)
  })

  it('shows assembly editor toggle when assembly steps exist', () => {
    const propsWithAssembly = {
      ...baseProps,
      manifest: { ...baseProps.manifest, assembly_steps: [{ id: 's1' }] },
    }
    render(<StudioSidebar {...propsWithAssembly} />)
    expect(screen.getAllByText('Edit Assembly Guide').length).toBeGreaterThan(0)
  })

  it('hides assembly editor toggle when no assembly steps', () => {
    render(<StudioSidebar {...baseProps} />)
    expect(screen.queryByText('Edit Assembly Guide')).not.toBeInTheDocument()
  })

  it('renders mobile menu button with screen reader text', () => {
    render(<StudioSidebar {...baseProps} />)
    expect(screen.getByText('Open controls')).toBeInTheDocument()
  })
})
