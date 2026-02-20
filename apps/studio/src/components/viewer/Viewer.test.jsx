import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock react-three/fiber Canvas and related components
vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }) => <div data-testid="mock-canvas">{children}</div>,
  useLoader: () => null,
}))

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  Grid: () => null,
  Environment: () => null,
  Edges: () => null,
  Bounds: ({ children }) => <>{children}</>,
  GizmoHelper: () => null,
  GizmoViewport: () => null,
}))

vi.mock('three/examples/jsm/loaders/STLLoader', () => ({
  STLLoader: class { },
}))

vi.mock('../../contexts/LanguageProvider', () => ({
  useLanguage: () => ({
    language: 'en',
    t: (key) => key,
  }),
}))

vi.mock('../../contexts/ThemeProvider', () => ({
  useTheme: () => ({ theme: 'light' }),
}))

vi.mock('../../contexts/ManifestProvider', () => ({
  useManifest: () => ({
    getCameraViews: () => [
      { id: 'iso', label: 'Iso', position: [50, 50, 50] },
      { id: 'top', label: 'Top', position: [0, 0, 100] },
      { id: 'front', label: 'Front', position: [0, 100, 0] },
    ],
    getViewerConfig: () => ({ default_color: '#e5e7eb' }),
    getLabel: (view) => view.label || view.id,
    getMode: () => null,
    manifest: {},
  }),
}))

vi.mock('../feedback/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }) => <>{children}</>,
}))

vi.mock('./SceneController', () => ({
  default: () => null,
}))

vi.mock('./NumberedAxes', () => ({
  default: () => <div data-testid="numbered-axes" />,
}))

vi.mock('./AnimatedGrid', () => ({
  default: () => null,
}))

vi.mock('../../lib/printEstimator', () => ({
  computeVolumeMm3: () => 0,
  computeBoundingBox: () => ({ width: 10, depth: 10, height: 10 }),
}))

import Viewer from './Viewer'

describe('Viewer', () => {
  const defaultProps = {
    parts: [],
    colors: {},
    wireframe: false,
    loading: false,
    progress: 0,
    progressPhase: null,
    animating: false,
    setAnimating: vi.fn(),
    mode: 'default',
    params: {},
  }

  it('renders the 3D canvas container', () => {
    render(<Viewer {...defaultProps} />)
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  it('shows loading overlay when loading is true', () => {
    render(<Viewer {...defaultProps} loading={true} progress={42} />)
    expect(screen.getByText('loader.loading')).toBeInTheDocument()
    expect(screen.getByText('42%')).toBeInTheDocument()
  })

  it('does not show loading overlay when loading is false', () => {
    render(<Viewer {...defaultProps} loading={false} />)
    expect(screen.queryByText('loader.loading')).not.toBeInTheDocument()
  })

  it('shows progress phase when provided during loading', () => {
    render(<Viewer {...defaultProps} loading={true} progress={50} progressPhase="Compiling" />)
    expect(screen.getByText('Compiling')).toBeInTheDocument()
  })

  it('renders camera view buttons from manifest', () => {
    render(<Viewer {...defaultProps} />)
    expect(screen.getByText('Iso')).toBeInTheDocument()
    expect(screen.getByText('Top')).toBeInTheDocument()
    expect(screen.getByText('Front')).toBeInTheDocument()
  })

  it('renders axes toggle button', () => {
    render(<Viewer {...defaultProps} />)
    const axesBtn = screen.getByTitle('viewer.hide_axes')
    expect(axesBtn).toBeInTheDocument()
  })

  it('toggles axes visibility on click', () => {
    render(<Viewer {...defaultProps} />)
    const axesBtn = screen.getByTitle('viewer.hide_axes')
    fireEvent.click(axesBtn)
    // After click, title should change to show_axes
    expect(screen.getByTitle('viewer.show_axes')).toBeInTheDocument()
  })

  it('does not show animation button when mode is not grid', () => {
    render(<Viewer {...defaultProps} mode="default" />)
    expect(screen.queryByTitle('viewer.play_anim')).not.toBeInTheDocument()
  })

  it('shows animation button when mode is grid', () => {
    render(<Viewer {...defaultProps} mode="grid" />)
    expect(screen.getByTitle('viewer.play_anim')).toBeInTheDocument()
  })

  it('calls setAnimating when animation button is clicked', () => {
    const setAnimating = vi.fn()
    render(<Viewer {...defaultProps} mode="grid" setAnimating={setAnimating} />)
    fireEvent.click(screen.getByTitle('viewer.play_anim'))
    expect(setAnimating).toHaveBeenCalledOnce()
  })

  it('highlights active camera view button', () => {
    render(<Viewer {...defaultProps} />)
    const isoBtn = screen.getByText('Iso')
    // Initial view is 'iso', so it should have the active class
    expect(isoBtn.className).toContain('bg-primary')
  })

  it('switches active view on camera button click', () => {
    render(<Viewer {...defaultProps} />)
    const topBtn = screen.getByText('Top')
    fireEvent.click(topBtn)
    expect(topBtn.className).toContain('bg-primary')
  })
})
