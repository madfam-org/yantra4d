import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('../viewer/Viewer', () => ({
  default: React.forwardRef(function MockViewer(props) {
    return <div data-testid="viewer" data-loading={props.loading} />
  }),
}))

vi.mock('../export/PrintEstimateOverlay', () => ({
  default: function MockOverlay(props) {
    return props.volumeMm3 ? <div data-testid="print-overlay" /> : null
  },
}))

vi.mock('./ShortcutHelpDialog', () => ({
  default: function MockShortcutHelp({ open }) {
    return open ? <div data-testid="shortcut-help" /> : null
  },
}))

vi.mock('./ModelInfoPanel', () => ({
  default: function MockModelInfo() {
    return <div data-testid="model-info" />
  },
}))

// Mock Contexts
vi.mock('../../contexts/project/ProjectProvider', () => ({
  useProject: vi.fn(),
}))
vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: vi.fn(),
}))
vi.mock('../../hooks/system/useUnitSystem', () => ({
  useUnitSystem: () => ({ unit: 'mm', format: (v) => `${v}mm`, formatVolume: (v, p = 0) => `${v.toFixed(p)} mm³`, label: 'mm', toggle: vi.fn() }),
}))

import StudioMainView from './StudioMainView'
import { useProject } from '../../contexts/project/ProjectProvider'
import { useLanguage } from '../../contexts/system/LanguageProvider'

const t = (key) => ({
  'status.rendering': 'Rendering',
  'status.ready': 'Ready',
}[key] || key)

const baseContext = {
  viewerRef: { current: null },
  consoleRef: { current: null },
  parts: [],
  colors: {},
  wireframe: false,
  loading: false,
  progress: 0,
  progressPhase: '',
  animating: false,
  setAnimating: vi.fn(),
  mode: 'full',
  params: {},
  printEstimate: null,
  setPrintEstimate: vi.fn(),
  assemblyActive: false,
  highlightedParts: [],
  visibleParts: [],
  headDiffMode: false,
  headParts: [],
  logs: '',
  orthoCamera: false,
  setOrthoCamera: vi.fn(),
  clippingEnabled: false,
  clippingAxis: 'y',
  clippingPosition: 0.5,
  measureMode: false,
  measurements: [],
  setMeasurements: vi.fn(),
  explodeFactor: 0,
  lightIntensity: 1,
  environmentPreset: 'studio',
  thicknessData: null,
  overhangData: null,
  shortcutHelpOpen: false,
  setShortcutHelpOpen: vi.fn(),
  boundingBox: false,
}

beforeEach(() => {
  vi.clearAllMocks()
  useProject.mockReturnValue(baseContext)
  useLanguage.mockReturnValue({ t })
})

describe('StudioMainView', () => {
  it('renders viewer and console log area', () => {
    render(<StudioMainView />)
    expect(screen.getByTestId('viewer')).toBeInTheDocument()
    // Mobile + desktop console panels both present in DOM
    expect(screen.getAllByRole('log').length).toBeGreaterThanOrEqual(1)
  })

  it('sets aria-busy when loading', () => {
    useProject.mockReturnValue({ ...baseContext, loading: true })
    render(<StudioMainView />)
    expect(screen.getByTestId('viewer').closest('[aria-busy]')).toHaveAttribute('aria-busy', 'true')
  })

  it('does not set aria-busy when idle', () => {
    render(<StudioMainView />)
    expect(screen.getByTestId('viewer').closest('[aria-busy]')).toHaveAttribute('aria-busy', 'false')
  })

  it('shows rendering status chip when loading', () => {
    useProject.mockReturnValue({ ...baseContext, loading: true, progress: 5, progressPhase: 'meshing' })
    render(<StudioMainView />)
    // The chip contains all info in a single element
    expect(screen.getByText(/Rendering.*5s.*meshing/)).toBeInTheDocument()
  })

  it('shows ready status chip when parts available', () => {
    useProject.mockReturnValue({ ...baseContext, parts: [{ id: 'body' }] })
    render(<StudioMainView />)
    expect(screen.getByText('Ready')).toBeInTheDocument()
  })

  it('shows no status chip when idle with no parts', () => {
    render(<StudioMainView />)
    expect(screen.queryByText('Rendering')).not.toBeInTheDocument()
    expect(screen.queryByText('Ready')).not.toBeInTheDocument()
  })

  it('announces render status via live region', () => {
    // Initial render loading
    useProject.mockReturnValue({ ...baseContext, loading: true })
    const { rerender, container } = render(<StudioMainView />)
    // The sr-only live region is the one with class "sr-only"
    const liveRegion = container.querySelector('.sr-only[aria-live="polite"]')
    expect(liveRegion).toBeInTheDocument()
    expect(liveRegion.textContent).toBe('Rendering in progress')

    // Update to complete
    useProject.mockReturnValue({ ...baseContext, loading: false, parts: [{ id: 'body' }] })
    rerender(<StudioMainView />)
    expect(liveRegion.textContent).toContain('Render complete')
  })

  it('displays console logs', () => {
    useProject.mockReturnValue({ ...baseContext, logs: 'ECHO: param=5' })
    render(<StudioMainView />)
    // Logs appear in both mobile (collapsed preview) and desktop console panels
    expect(screen.getAllByText('ECHO: param=5').length).toBeGreaterThanOrEqual(1)
  })

  it('renders mobile console toggle button', () => {
    render(<StudioMainView />)
    expect(screen.getByLabelText('Toggle console panel')).toBeInTheDocument()
  })

  it('renders print estimate overlay when estimate exists', () => {
    useProject.mockReturnValue({ ...baseContext, printEstimate: { volumeMm3: 1200, boundingBox: {} } })
    render(<StudioMainView />)
    expect(screen.getByTestId('print-overlay')).toBeInTheDocument()
  })

  it('does not render print estimate overlay when no estimate', () => {
    render(<StudioMainView />)
    expect(screen.queryByTestId('print-overlay')).not.toBeInTheDocument()
  })
})
