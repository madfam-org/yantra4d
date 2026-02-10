import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('./Viewer', () => ({
  default: React.forwardRef(function MockViewer(props) {
    return <div data-testid="viewer" data-loading={props.loading} />
  }),
}))

vi.mock('./PrintEstimateOverlay', () => ({
  default: function MockOverlay(props) {
    return props.volumeMm3 ? <div data-testid="print-overlay" /> : null
  },
}))

import StudioMainView from './StudioMainView'

const t = (key) => ({
  'status.rendering': 'Rendering',
  'status.ready': 'Ready',
}[key] || key)

const baseProps = {
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
  t,
}

describe('StudioMainView', () => {
  it('renders viewer and console log area', () => {
    render(<StudioMainView {...baseProps} />)
    expect(screen.getByTestId('viewer')).toBeInTheDocument()
    expect(screen.getByRole('log')).toBeInTheDocument()
  })

  it('sets aria-busy when loading', () => {
    render(<StudioMainView {...baseProps} loading={true} />)
    expect(screen.getByTestId('viewer').closest('[aria-busy]')).toHaveAttribute('aria-busy', 'true')
  })

  it('does not set aria-busy when idle', () => {
    render(<StudioMainView {...baseProps} />)
    expect(screen.getByTestId('viewer').closest('[aria-busy]')).toHaveAttribute('aria-busy', 'false')
  })

  it('shows rendering status chip when loading', () => {
    render(<StudioMainView {...baseProps} loading={true} progress={5} progressPhase="meshing" />)
    // The chip contains all info in a single element
    expect(screen.getByText(/Rendering.*5s.*meshing/)).toBeInTheDocument()
  })

  it('shows ready status chip when parts available', () => {
    render(<StudioMainView {...baseProps} parts={[{ id: 'body' }]} />)
    expect(screen.getByText('Ready')).toBeInTheDocument()
  })

  it('shows no status chip when idle with no parts', () => {
    render(<StudioMainView {...baseProps} />)
    expect(screen.queryByText('Rendering')).not.toBeInTheDocument()
    expect(screen.queryByText('Ready')).not.toBeInTheDocument()
  })

  it('announces render status via live region', () => {
    const { rerender, container } = render(<StudioMainView {...baseProps} loading={true} />)
    const liveRegion = container.querySelector('[aria-live="polite"]')
    expect(liveRegion).toBeInTheDocument()
    expect(liveRegion.textContent).toBe('Rendering in progress')

    rerender(<StudioMainView {...baseProps} loading={false} parts={[{ id: 'body' }]} />)
    expect(liveRegion.textContent).toBe('Render complete')
  })

  it('displays console logs', () => {
    render(<StudioMainView {...baseProps} logs="ECHO: param=5" />)
    expect(screen.getByText('ECHO: param=5')).toBeInTheDocument()
  })

  it('renders print estimate overlay when estimate exists', () => {
    render(<StudioMainView {...baseProps} printEstimate={{ volumeMm3: 1200, boundingBox: {} }} />)
    expect(screen.getByTestId('print-overlay')).toBeInTheDocument()
  })

  it('does not render print estimate overlay when no estimate', () => {
    render(<StudioMainView {...baseProps} />)
    expect(screen.queryByTestId('print-overlay')).not.toBeInTheDocument()
  })
})
