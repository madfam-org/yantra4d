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

// Mock Contexts
vi.mock('../../contexts/ProjectProvider', () => ({
  useProject: vi.fn(),
}))
vi.mock('../../contexts/LanguageProvider', () => ({
  useLanguage: vi.fn(),
}))

import StudioSidebar from './StudioSidebar'
import { useProject } from '../../contexts/ProjectProvider'
import { useLanguage } from '../../contexts/LanguageProvider'

const baseContext = {
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
  handleAssemblyStepChange: vi.fn(),
  assemblyEditorOpen: false,
  setAssemblyEditorOpen: vi.fn(),
  viewerRef: { current: null },
  projectSlug: 'test',
}

beforeEach(() => {
  vi.clearAllMocks()
  useProject.mockReturnValue(baseContext)
  useLanguage.mockReturnValue({
    t: (key) => key,
    language: 'en',
  })
})

describe('StudioSidebar', () => {
  it('renders mode tabs for each mode in manifest', () => {
    render(<StudioSidebar />)
    expect(screen.getAllByText('Full').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Plate').length).toBeGreaterThan(0)
  })

  it('renders generate button', () => {
    render(<StudioSidebar />)
    expect(screen.getAllByText('btn.gen').length).toBeGreaterThan(0)
  })

  it('shows processing text when loading', () => {
    useProject.mockReturnValue({ ...baseContext, loading: true })
    render(<StudioSidebar />)
    expect(screen.getAllByText('btn.proc').length).toBeGreaterThan(0)
  })

  it('shows cancel button when loading', () => {
    useProject.mockReturnValue({ ...baseContext, loading: true })
    render(<StudioSidebar />)
    expect(screen.getAllByText('btn.cancel').length).toBeGreaterThan(0)
  })

  it('disables generate button when loading', () => {
    useProject.mockReturnValue({ ...baseContext, loading: true })
    render(<StudioSidebar />)
    const genBtns = screen.getAllByText('btn.proc')
    genBtns.forEach(btn => {
      expect(btn.closest('button')).toBeDisabled()
    })
  })

  it('disables generate button when constraint errors', () => {
    useProject.mockReturnValue({ ...baseContext, constraintErrors: true })
    render(<StudioSidebar />)
    const genBtns = screen.getAllByText('btn.gen')
    genBtns.forEach(btn => {
      expect(btn.closest('button')).toBeDisabled()
    })
  })

  it('disables verify button when no parts', () => {
    useProject.mockReturnValue({ ...baseContext, parts: [] })
    render(<StudioSidebar />)
    const verifyBtns = screen.getAllByText('btn.verify')
    verifyBtns.forEach(btn => {
      expect(btn.closest('button')).toBeDisabled()
    })
  })

  it('enables verify button when parts available', () => {
    useProject.mockReturnValue({ ...baseContext, parts: [{ id: 'body' }] })
    render(<StudioSidebar />)
    const verifyBtns = screen.getAllByText('btn.verify')
    verifyBtns.forEach(btn => {
      expect(btn.closest('button')).not.toBeDisabled()
    })
  })

  it('calls handleGenerate when clicking generate button', () => {
    render(<StudioSidebar />)
    const genBtns = screen.getAllByText('btn.gen')
    fireEvent.click(genBtns[0].closest('button'))
    expect(baseContext.handleGenerate).toHaveBeenCalled()
  })

  it('calls handleReset when clicking reset button', () => {
    render(<StudioSidebar />)
    const resetBtns = screen.getAllByText('btn.reset')
    fireEvent.click(resetBtns[0].closest('button'))
    expect(baseContext.handleReset).toHaveBeenCalled()
  })

  it('renders child panels: controls, export, bom, assembly', () => {
    render(<StudioSidebar />)
    expect(screen.getAllByTestId('controls').length).toBeGreaterThan(0)
    expect(screen.getAllByTestId('export-panel').length).toBeGreaterThan(0)
    expect(screen.getAllByTestId('bom-panel').length).toBeGreaterThan(0)
    expect(screen.getAllByTestId('assembly-view').length).toBeGreaterThan(0)
  })

  it('shows assembly editor toggle when assembly steps exist', () => {
    useProject.mockReturnValue({
      ...baseContext,
      manifest: { ...baseContext.manifest, assembly_steps: [{ id: 's1' }] },
    })
    render(<StudioSidebar />)
    expect(screen.getAllByText('Edit Assembly Guide').length).toBeGreaterThan(0)
  })

  it('hides assembly editor toggle when no assembly steps', () => {
    render(<StudioSidebar />)
    expect(screen.queryByText('Edit Assembly Guide')).not.toBeInTheDocument()
  })

  it('renders mobile menu button with screen reader text', () => {
    render(<StudioSidebar />)
    expect(screen.getByText('Open controls')).toBeInTheDocument()
  })
})
