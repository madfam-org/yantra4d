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

// Mock Contexts
vi.mock('../../contexts/project/ProjectProvider', () => ({
  useProject: vi.fn(),
}))
vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: vi.fn(),
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
  logs: '',
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
    expect(screen.getByRole('log')).toBeInTheDocument()
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
    const liveRegion = container.querySelector('[aria-live="polite"]')
    expect(liveRegion).toBeInTheDocument()
    expect(liveRegion.textContent).toBe('Rendering in progress')

    // Update to complete
    useProject.mockReturnValue({ ...baseContext, loading: false, parts: [{ id: 'body' }] })
    rerender(<StudioMainView />)
    expect(liveRegion.textContent).toBe('Render complete')
  })

  it('displays console logs', () => {
    useProject.mockReturnValue({ ...baseContext, logs: 'ECHO: param=5' })
    render(<StudioMainView />)
    expect(screen.getByText('ECHO: param=5')).toBeInTheDocument()
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
