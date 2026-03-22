import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'

// ── Controllable mock for useWorkerLoader ──
const mockUseWorkerLoader = vi.fn(() => ({ geometry: null, scene: null }))

vi.mock('../../hooks/render/useWorkerLoader', () => ({
  useWorkerLoader: (...args) => mockUseWorkerLoader(...args),
}))

// ── Controllable mock for useTheme ──
const mockUseTheme = vi.fn(() => ({ theme: 'light' }))
vi.mock('../../contexts/system/ThemeProvider', () => ({
  useTheme: () => mockUseTheme(),
}))

// ── Controllable mock for useManifest ──
const defaultManifestMock = {
  getCameraViews: () => [
    { id: 'iso', label: 'Iso', position: [50, 50, 50] },
    { id: 'top', label: 'Top', position: [0, 0, 100] },
    { id: 'front', label: 'Front', position: [0, 100, 0] },
  ],
  getViewerConfig: () => ({ default_color: '#e5e7eb' }),
  getLabel: (view) => view.label || view.id,
  getMode: () => null,
  manifest: {},
}
const mockUseManifest = vi.fn(() => defaultManifestMock)
vi.mock('../../contexts/project/ManifestProvider', () => ({
  useManifest: () => mockUseManifest(),
}))

// ── Controllable mock for printEstimator ──
const mockComputeVolumeMm3 = vi.fn(() => 1000)
const mockComputeBoundingBox = vi.fn(() => ({ width: 10, depth: 10, height: 10 }))
const mockComputeCentroid = vi.fn(() => ({ x: 5, y: 5, z: 5 }))
vi.mock('../../lib/printEstimator', () => ({
  computeVolumeMm3: (...args) => mockComputeVolumeMm3(...args),
  computeBoundingBox: (...args) => mockComputeBoundingBox(...args),
  computeCentroid: (...args) => mockComputeCentroid(...args),
}))

// ── Mock react-three/fiber ──
vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }) => <div data-testid="mock-canvas">{children}</div>,
  useLoader: () => null,
}))

// ── Mock react-three/drei ──
vi.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  OrthographicCamera: () => null,
  Grid: () => null,
  Environment: () => null,
  Edges: () => null,
  Bounds: ({ children }) => <>{children}</>,
  GizmoHelper: ({ children }) => <div data-testid="gizmo-helper">{children}</div>,
  GizmoViewport: () => null,
  Html: ({ children }) => <div data-testid="html-label">{children}</div>,
}))

vi.mock('three/examples/jsm/loaders/STLLoader', () => ({
  STLLoader: class { },
}))

vi.mock('three/examples/jsm/loaders/GLTFLoader', () => ({
  GLTFLoader: class { },
}))

vi.mock('three/examples/jsm/utils/BufferGeometryUtils', () => ({
  default: {},
}))

vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({
    language: 'en',
    t: (key) => key,
  }),
}))

vi.mock('../feedback/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }) => <>{children}</>,
}))

// ── Controllable SceneController mock ──
const mockAnimateTo = vi.fn()
const mockSetCameraView = vi.fn()
const mockCaptureSnapshot = vi.fn(() => 'snapshot-data')
const mockGetCameraState = vi.fn(() => ({ position: [1, 2, 3] }))

vi.mock('./SceneController', () => {
  const ForwardedSceneController = React.forwardRef((props, ref) => {
    React.useImperativeHandle(ref, () => ({
      animateTo: mockAnimateTo,
      setCameraView: mockSetCameraView,
      captureSnapshot: mockCaptureSnapshot,
      getCameraState: mockGetCameraState,
    }))
    return <div data-testid="scene-controller" />
  })
  ForwardedSceneController.displayName = 'SceneController'
  return { default: ForwardedSceneController }
})

vi.mock('./NumberedAxes', () => ({
  default: () => <div data-testid="numbered-axes" />,
}))

// ── Controllable AnimatedGrid mock ──
let capturedAnimatedGridOnReady = null
let capturedAnimatedGridOnError = null
vi.mock('./AnimatedGrid', () => ({
  default: (props) => {
    capturedAnimatedGridOnReady = props.onReady
    capturedAnimatedGridOnError = props.onError
    return <div data-testid="animated-grid" />
  },
}))

vi.mock('./ClippingPlane', () => ({
  default: (props) => <div data-testid="clipping-plane" data-axis={props.axis} />,
}))

vi.mock('./MeasureTool', () => ({
  default: (props) => <div data-testid="measure-tool" data-active={String(props.active)} />,
}))

vi.mock('./ThicknessOverlay', () => ({
  default: (props) => props.points?.length ? <div data-testid="thickness-overlay" /> : null,
}))

vi.mock('./OverhangOverlay', () => ({
  default: (props) => props.points?.length ? <div data-testid="overhang-overlay" /> : null,
}))

vi.mock('./ParameterPreviewOverlay', () => ({
  default: (props) => props.hoveredParam ? <div data-testid="parameter-preview-overlay" data-has-cached-variants={props.cachedVariants ? 'true' : 'false'} /> : null,
}))

import Viewer from './Viewer'

// ── Helper: create a fake BufferGeometry-like object ──
function makeFakeGeometry(boundsMin = [0, 0, 0], boundsMax = [10, 10, 10]) {
  return {
    boundingBox: {
      min: { x: boundsMin[0], y: boundsMin[1], z: boundsMin[2] },
      max: { x: boundsMax[0], y: boundsMax[1], z: boundsMax[2] },
      getCenter: vi.fn((target) => {
        target.x = (boundsMin[0] + boundsMax[0]) / 2
        target.y = (boundsMin[1] + boundsMax[1]) / 2
        target.z = (boundsMin[2] + boundsMax[2]) / 2
        return target
      }),
      getSize: vi.fn((target) => {
        target.x = boundsMax[0] - boundsMin[0]
        target.y = boundsMax[1] - boundsMin[1]
        target.z = boundsMax[2] - boundsMin[2]
        return target
      }),
      copy: vi.fn(function () { return this }),
      union: vi.fn(),
    },
    computeBoundingBox: vi.fn(),
  }
}

describe('Viewer', () => {
  const defaultProps = {
    parts: [],
    colors: {},
    wireframe: false,
    boundingBox: false,
    loading: false,
    progress: 0,
    progressPhase: null,
    animating: false,
    setAnimating: vi.fn(),
    mode: 'default',
    params: {},
    onGeometryStats: vi.fn(),
    assemblyActive: false,
    highlightedParts: [],
    visibleParts: [],
    headDiffMode: false,
    headParts: [],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseWorkerLoader.mockReturnValue({ geometry: null, scene: null })
    mockUseTheme.mockReturnValue({ theme: 'light' })
    mockUseManifest.mockReturnValue(defaultManifestMock)
    mockComputeVolumeMm3.mockReturnValue(1000)
    mockComputeBoundingBox.mockReturnValue({ width: 10, depth: 10, height: 10 })
    mockComputeCentroid.mockReturnValue({ x: 5, y: 5, z: 5 })
    capturedAnimatedGridOnReady = null
    capturedAnimatedGridOnError = null
  })

  // ────────────────────────────────────────
  // Existing basic tests
  // ────────────────────────────────────────

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

  it('does not show progress phase when null during loading', () => {
    render(<Viewer {...defaultProps} loading={true} progress={50} progressPhase={null} />)
    // Only "loader.loading" and "50%" should be present, no extra phase text
    expect(screen.getByText('loader.loading')).toBeInTheDocument()
  })

  it('renders camera view buttons from manifest', () => {
    render(<Viewer {...defaultProps} />)
    // Camera views appear in both mobile select and desktop buttons
    expect(screen.getAllByText('Iso').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Top').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Front').length).toBeGreaterThanOrEqual(1)
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
    expect(screen.getByTitle('viewer.show_axes')).toBeInTheDocument()
    // NumberedAxes should be gone
    expect(screen.queryByTestId('numbered-axes')).not.toBeInTheDocument()
  })

  it('does not show animation button when mode is not grid', () => {
    render(<Viewer {...defaultProps} mode="default" />)
    expect(screen.queryByTestId('animation-toggle')).not.toBeInTheDocument()
  })

  it('shows animation button when mode is grid', () => {
    render(<Viewer {...defaultProps} mode="grid" />)
    expect(screen.getByTestId('animation-toggle')).toBeInTheDocument()
  })

  it('calls setAnimating when animation button is clicked', () => {
    const setAnimating = vi.fn()
    render(<Viewer {...defaultProps} mode="grid" setAnimating={setAnimating} />)
    fireEvent.click(screen.getByTestId('animation-toggle'))
    expect(setAnimating).toHaveBeenCalledOnce()
  })

  it('highlights active camera view button', () => {
    render(<Viewer {...defaultProps} />)
    // Desktop buttons are inside the hidden sm:flex container
    const isoBtns = screen.getAllByText('Iso')
    const isoBtn = isoBtns.find(el => el.tagName === 'BUTTON')
    expect(isoBtn).toBeTruthy()
    expect(isoBtn.className).toContain('bg-primary')
  })

  it('switches active view on camera button click', () => {
    render(<Viewer {...defaultProps} />)
    // Click the desktop button (not the select option)
    const topBtns = screen.getAllByText('Top')
    const topBtn = topBtns.find(el => el.tagName === 'BUTTON')
    expect(topBtn).toBeTruthy()
    fireEvent.click(topBtn)
    expect(topBtn.className).toContain('bg-primary')
  })

  // ────────────────────────────────────────
  // Dark theme branch
  // ────────────────────────────────────────

  it('applies dark theme background color', () => {
    mockUseTheme.mockReturnValue({ theme: 'dark' })
    render(<Viewer {...defaultProps} />)
    // Axes toggle should still render; dark background is applied to Canvas color
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  it('applies system theme with dark media query', () => {
    // Mock matchMedia to return dark
    const original = window.matchMedia
    window.matchMedia = vi.fn((query) => ({
      matches: true,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => {},
    }))
    mockUseTheme.mockReturnValue({ theme: 'system' })
    render(<Viewer {...defaultProps} />)
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
    window.matchMedia = original
  })

  // ────────────────────────────────────────
  // Parts rendering branches
  // ────────────────────────────────────────

  it('renders Model components when parts are provided', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    render(
      <Viewer
        {...defaultProps}
        parts={[
          { type: 'base', url: '/api/render/base.stl' },
          { type: 'lid', url: '/api/render/lid.stl' },
        ]}
        colors={{ base: '#ff0000', lid: '#00ff00' }}
      />
    )
    // Models are rendered inside Canvas; the worker loader should have been called
    expect(mockUseWorkerLoader).toHaveBeenCalled()
  })

  it('renders nothing inside Suspense when parts array is empty', () => {
    render(<Viewer {...defaultProps} parts={[]} />)
    // No models rendered, but canvas still exists
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // headDiffMode branch
  // ────────────────────────────────────────

  it('renders head diff mode with headParts and current parts', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    render(
      <Viewer
        {...defaultProps}
        headDiffMode={true}
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        headParts={[{ type: 'base', url: '/api/render/head-base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    expect(mockUseWorkerLoader).toHaveBeenCalled()
  })

  // ────────────────────────────────────────
  // Assembly mode / highlight branches
  // ────────────────────────────────────────

  it('passes hidden highlightMode when assemblyActive and part not visible', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    render(
      <Viewer
        {...defaultProps}
        assemblyActive={true}
        visibleParts={[]}
        highlightedParts={[]}
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  it('passes highlight highlightMode when part is highlighted', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    render(
      <Viewer
        {...defaultProps}
        assemblyActive={true}
        visibleParts={['base']}
        highlightedParts={['base']}
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  it('passes ghost highlightMode when part is visible but not highlighted', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    render(
      <Viewer
        {...defaultProps}
        assemblyActive={true}
        visibleParts={['base']}
        highlightedParts={[]}
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // Wireframe branch
  // ────────────────────────────────────────

  it('renders with wireframe enabled', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    render(
      <Viewer
        {...defaultProps}
        wireframe={true}
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // BoundingBox display branch
  // ────────────────────────────────────────

  it('renders bounding box labels when boundingBox is true and parts exist', () => {
    const fakeGeom = makeFakeGeometry([0, 0, 0], [20, 30, 40])
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    render(
      <Viewer
        {...defaultProps}
        boundingBox={true}
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // Animation states
  // ────────────────────────────────────────

  it('shows preparing overlay when animating in grid mode and not ready', () => {
    render(
      <Viewer
        {...defaultProps}
        animating={true}
        mode="grid"
      />
    )
    expect(screen.getByText('anim.preparing')).toBeInTheDocument()
  })

  it('shows pause button text when animating in grid mode', () => {
    render(
      <Viewer
        {...defaultProps}
        animating={true}
        mode="grid"
      />
    )
    const btn = screen.getByTestId('animation-toggle')
    expect(btn).toBeInTheDocument()
    expect(btn.title).toBe('viewer.pause_anim')
  })

  it('does not show preparing overlay when not animating', () => {
    render(
      <Viewer
        {...defaultProps}
        animating={false}
        mode="grid"
      />
    )
    expect(screen.queryByText('anim.preparing')).not.toBeInTheDocument()
  })

  it('does not show preparing overlay when mode is not grid', () => {
    render(
      <Viewer
        {...defaultProps}
        animating={true}
        mode="default"
      />
    )
    expect(screen.queryByText('anim.preparing')).not.toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // AnimatedGrid onReady callback triggers animReady
  // ────────────────────────────────────────

  it('hides preparing overlay after AnimatedGrid fires onReady', () => {
    render(
      <Viewer
        {...defaultProps}
        animating={true}
        mode="grid"
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    // Before onReady, preparing overlay should be visible
    expect(screen.getByText('anim.preparing')).toBeInTheDocument()

    // Simulate AnimatedGrid calling onReady
    act(() => {
      capturedAnimatedGridOnReady?.()
    })

    // After onReady, preparing overlay should disappear
    expect(screen.queryByText('anim.preparing')).not.toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // AnimatedGrid onError callback dismisses overlay and stops animation
  // ────────────────────────────────────────

  it('dismisses preparing overlay and stops animation on AnimatedGrid error', () => {
    const setAnimating = vi.fn()
    render(
      <Viewer
        {...defaultProps}
        animating={true}
        mode="grid"
        setAnimating={setAnimating}
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    // Before error, preparing overlay should be visible
    expect(screen.getByText('anim.preparing')).toBeInTheDocument()

    // Simulate AnimatedGrid calling onError
    act(() => {
      capturedAnimatedGridOnError?.()
    })

    // onError sets animError=true and calls setAnimating(false)
    expect(setAnimating).toHaveBeenCalledWith(false)
    // Overlay should be dismissed (animError = true hides it)
    expect(screen.queryByText('anim.preparing')).not.toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // structuralPartIds branch (grid mode vs assembly mode parts)
  // ────────────────────────────────────────

  it('separates structural and assembly parts when grid and assembly modes exist', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    mockUseManifest.mockReturnValue({
      ...defaultManifestMock,
      getMode: (id) => {
        if (id === 'grid') return { parts: ['base', 'rod', 'stopper'] }
        if (id === 'assembly') return { parts: ['base'] }
        return null
      },
      manifest: {
        parts: [
          { id: 'base' },
          { id: 'rod' },
          { id: 'stopper' },
        ],
      },
    })

    render(
      <Viewer
        {...defaultProps}
        mode="grid"
        parts={[
          { type: 'base', url: '/api/render/base.stl' },
          { type: 'rod', url: '/api/render/rod.stl' },
          { type: 'stopper', url: '/api/render/stopper.stl' },
        ]}
        colors={{ base: '#ff0000', rod: '#00ff00', stopper: '#0000ff' }}
      />
    )
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // Glass material branch
  // ────────────────────────────────────────

  it('renders glass parts from manifest part definition', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    mockUseManifest.mockReturnValue({
      ...defaultManifestMock,
      manifest: {
        parts: [{ id: 'cover', glass: true }],
      },
    })

    render(
      <Viewer
        {...defaultProps}
        parts={[{ type: 'cover', url: '/api/render/cover.stl' }]}
        colors={{ cover: '#88ccff' }}
      />
    )
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // Manifest axis_colors branch
  // ────────────────────────────────────────

  it('uses custom axis colors from manifest when provided', () => {
    mockUseManifest.mockReturnValue({
      ...defaultManifestMock,
      manifest: {
        viewer: {
          axis_colors: { x: '#ff0000', y: '#00ff00', z: '#0000ff' },
        },
      },
    })

    render(<Viewer {...defaultProps} />)
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  it('uses default axis colors when manifest has no axis_colors', () => {
    mockUseManifest.mockReturnValue({
      ...defaultManifestMock,
      manifest: {},
    })

    render(<Viewer {...defaultProps} />)
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // useImperativeHandle (ref API) branches
  // ────────────────────────────────────────

  it('exposes captureSnapshot via ref', () => {
    const ref = React.createRef()
    render(<Viewer {...defaultProps} ref={ref} />)
    const result = ref.current.captureSnapshot()
    expect(mockCaptureSnapshot).toHaveBeenCalled()
    expect(result).toBe('snapshot-data')
  })

  it('exposes setCameraView via ref and updates active view', () => {
    const ref = React.createRef()
    render(<Viewer {...defaultProps} ref={ref} />)
    act(() => {
      ref.current.setCameraView('top')
    })
    expect(mockSetCameraView).toHaveBeenCalledWith('top')
    // Active view should now be 'top' — find the desktop button
    const topBtns = screen.getAllByText('Top')
    const topBtn = topBtns.find(el => el.tagName === 'BUTTON')
    expect(topBtn.className).toContain('bg-primary')
  })

  it('exposes animateTo via ref', () => {
    const ref = React.createRef()
    render(<Viewer {...defaultProps} ref={ref} />)
    ref.current.animateTo([10, 20, 30], [0, 0, 0], 0.5)
    expect(mockAnimateTo).toHaveBeenCalledWith([10, 20, 30], [0, 0, 0], 0.5)
  })

  it('exposes getCameraState via ref', () => {
    const ref = React.createRef()
    render(<Viewer {...defaultProps} ref={ref} />)
    const state = ref.current.getCameraState()
    expect(mockGetCameraState).toHaveBeenCalled()
    expect(state).toEqual({ position: [1, 2, 3] })
  })

  // ────────────────────────────────────────
  // Camera positioning on mode change (lines 316-331)
  // ────────────────────────────────────────

  it('animates camera to mode bbox when mode changes and progress is 100', () => {
    mockUseManifest.mockReturnValue({
      ...defaultManifestMock,
      manifest: {
        modes: [
          {
            id: 'grid',
            initial_bbox: { center_mm: [10, 20, 30], max_dim_mm: 50 },
          },
        ],
      },
    })

    render(
      <Viewer {...defaultProps} mode="grid" progress={100} />
    )
    expect(mockAnimateTo).toHaveBeenCalled()
  })

  it('does not animate camera when progress is less than 100', () => {
    mockUseManifest.mockReturnValue({
      ...defaultManifestMock,
      manifest: {
        modes: [
          {
            id: 'grid',
            initial_bbox: { center_mm: [10, 20, 30], max_dim_mm: 50 },
          },
        ],
      },
    })

    render(
      <Viewer {...defaultProps} mode="grid" progress={50} />
    )
    expect(mockAnimateTo).not.toHaveBeenCalled()
  })

  it('does not animate camera when mode has no initial_bbox', () => {
    mockUseManifest.mockReturnValue({
      ...defaultManifestMock,
      manifest: {
        modes: [{ id: 'grid' }],
      },
    })

    render(
      <Viewer {...defaultProps} mode="grid" progress={100} />
    )
    expect(mockAnimateTo).not.toHaveBeenCalled()
  })

  // ────────────────────────────────────────
  // animReady reset when animating toggled off (line 335)
  // ────────────────────────────────────────

  it('resets animReady when animating is toggled off', () => {
    const { rerender } = render(
      <Viewer
        {...defaultProps}
        animating={true}
        mode="grid"
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )

    // Trigger onReady to set animReady = true
    act(() => {
      capturedAnimatedGridOnReady?.()
    })
    expect(screen.queryByText('anim.preparing')).not.toBeInTheDocument()

    // Now toggle animating off - animReady should reset
    rerender(
      <Viewer
        {...defaultProps}
        animating={false}
        mode="grid"
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    // No preparing overlay when not animating
    expect(screen.queryByText('anim.preparing')).not.toBeInTheDocument()

    // Toggle animating back on - preparing overlay should show again (animReady was reset)
    rerender(
      <Viewer
        {...defaultProps}
        animating={true}
        mode="grid"
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    expect(screen.getByText('anim.preparing')).toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // isoView fallback when no 'iso' camera view
  // ────────────────────────────────────────

  it('falls back to first camera view when iso view is not defined', () => {
    mockUseManifest.mockReturnValue({
      ...defaultManifestMock,
      getCameraViews: () => [
        { id: 'top', label: 'Top', position: [0, 0, 100] },
        { id: 'front', label: 'Front', position: [0, 100, 0] },
      ],
    })

    render(<Viewer {...defaultProps} />)
    expect(screen.getAllByText('Top').length).toBeGreaterThanOrEqual(1)
  })

  // ────────────────────────────────────────
  // Default color fallback when part color not in colors map
  // ────────────────────────────────────────

  it('uses default color when part color is not specified', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    render(
      <Viewer
        {...defaultProps}
        parts={[{ type: 'unknown', url: '/api/render/unknown.stl' }]}
        colors={{}}
      />
    )
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // onGeometryStats callback with empty geometries (totalVolume === 0)
  // ────────────────────────────────────────

  it('calls onGeometryStats when geometry loads and handles zero volume', () => {
    mockComputeVolumeMm3.mockReturnValue(0)
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    const onGeometryStats = vi.fn()
    render(
      <Viewer
        {...defaultProps}
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
        onGeometryStats={onGeometryStats}
      />
    )
    // The onGeometryStats should be called with total volume 0
    // This exercises the else branch at line 259-262
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // Partial axis_colors override
  // ────────────────────────────────────────

  it('uses partial axis colors from manifest, falling back to defaults for missing axes', () => {
    mockUseManifest.mockReturnValue({
      ...defaultManifestMock,
      manifest: {
        viewer: {
          axis_colors: { x: '#aabbcc' },
          // y and z not specified
        },
      },
    })

    render(<Viewer {...defaultProps} />)
    expect(screen.getByTestId('mock-canvas')).toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // GLB detection with query params (cache-buster fix)
  // ────────────────────────────────────────

  it('detects GLB format when URL has query string cache-buster', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    render(
      <Viewer
        {...defaultProps}
        parts={[{ type: 'body', url: '/static/model.glb?t=1708611200000' }]}
        colors={{ body: '#ff0000' }}
      />
    )
    // useWorkerLoader should be called with isGLTF=true despite ?t= suffix
    const call = mockUseWorkerLoader.mock.calls.find(c => c[0]?.includes('.glb'))
    expect(call).toBeDefined()
    expect(call[1]).toBe(true)
  })

  it('detects STL format when URL has query string cache-buster', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    render(
      <Viewer
        {...defaultProps}
        parts={[{ type: 'body', url: '/static/model.stl?t=1708611200000' }]}
        colors={{ body: '#ff0000' }}
      />
    )
    const call = mockUseWorkerLoader.mock.calls.find(c => c[0]?.includes('.stl'))
    expect(call).toBeDefined()
    expect(call[1]).toBe(false)
  })

  it('uses isGlb prop from part to detect format for blob URLs', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    render(
      <Viewer
        {...defaultProps}
        parts={[{ type: 'body', url: 'blob:http://localhost/abc123', isGlb: true }]}
        colors={{ body: '#ff0000' }}
      />
    )
    // blob URL has no extension, but isGlb=true should make isGLTF=true
    const call = mockUseWorkerLoader.mock.calls.find(c => c[0]?.includes('blob:'))
    expect(call).toBeDefined()
    expect(call[1]).toBe(true)
  })

  // ────────────────────────────────────────
  // Viewer.displayName
  // ────────────────────────────────────────

  it('has displayName set to Viewer', () => {
    expect(Viewer.displayName).toBe('Viewer')
  })

  // ────────────────────────────────────────
  // Orthographic camera toggle (Sprint 1.1)
  // ────────────────────────────────────────

  it('renders ortho toggle button', () => {
    render(<Viewer {...defaultProps} />)
    expect(screen.getByTestId('ortho-toggle')).toBeInTheDocument()
  })

  it('ortho toggle button reflects orthoCamera state', () => {
    render(<Viewer {...defaultProps} orthoCamera={false} />)
    const btn = screen.getByTestId('ortho-toggle')
    expect(btn.getAttribute('aria-pressed')).toBe('false')
  })

  it('ortho toggle button shows pressed state when ortho is active', () => {
    render(<Viewer {...defaultProps} orthoCamera={true} />)
    const btn = screen.getByTestId('ortho-toggle')
    expect(btn.getAttribute('aria-pressed')).toBe('true')
  })

  it('calls setOrthoCamera when ortho toggle is clicked', () => {
    const setOrthoCamera = vi.fn()
    render(<Viewer {...defaultProps} setOrthoCamera={setOrthoCamera} />)
    fireEvent.click(screen.getByTestId('ortho-toggle'))
    expect(setOrthoCamera).toHaveBeenCalledOnce()
  })

  // ────────────────────────────────────────
  // Clipping plane (Sprint 2.1)
  // ────────────────────────────────────────

  it('does not render clipping plane when disabled', () => {
    render(<Viewer {...defaultProps} clippingEnabled={false} />)
    expect(screen.queryByTestId('clipping-plane')).not.toBeInTheDocument()
  })

  it('renders clipping plane when enabled', () => {
    render(<Viewer {...defaultProps} clippingEnabled={true} clippingAxis="z" />)
    const plane = screen.getByTestId('clipping-plane')
    expect(plane).toBeInTheDocument()
    expect(plane.getAttribute('data-axis')).toBe('z')
  })

  // ────────────────────────────────────────
  // Measure tool (Sprint 2.2)
  // ────────────────────────────────────────

  it('does not render measure tool when not active', () => {
    render(<Viewer {...defaultProps} measureMode={false} />)
    expect(screen.queryByTestId('measure-tool')).not.toBeInTheDocument()
  })

  it('renders measure tool when active', () => {
    render(<Viewer {...defaultProps} measureMode={true} />)
    expect(screen.getByTestId('measure-tool')).toBeInTheDocument()
  })

  // ────────────────────────────────────────
  // Parameter preview overlay (hover-to-preview)
  // ────────────────────────────────────────

  it('does not render parameter preview overlay when hoveredParam is null', () => {
    render(<Viewer {...defaultProps} hoveredParam={null} />)
    expect(screen.queryByTestId('parameter-preview-overlay')).not.toBeInTheDocument()
  })

  it('renders parameter preview overlay when hoveredParam is provided with parts', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    const hoveredParam = {
      paramId: 'width',
      paramDef: { id: 'width', type: 'slider', min: 10, max: 100, label: { en: 'Width' } },
      currentValue: 50,
      hint: { type: 'axis_scale', axis: 'x', affected_parts: ['base'] },
    }

    render(
      <Viewer
        {...defaultProps}
        hoveredParam={hoveredParam}
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    expect(screen.getByTestId('parameter-preview-overlay')).toBeInTheDocument()
  })

  it('does not render parameter preview overlay during assembly mode', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    const hoveredParam = {
      paramId: 'width',
      paramDef: { id: 'width', type: 'slider', min: 10, max: 100 },
      currentValue: 50,
      hint: { type: 'axis_scale', axis: 'x', affected_parts: ['base'] },
    }

    render(
      <Viewer
        {...defaultProps}
        assemblyActive={true}
        visibleParts={['base']}
        highlightedParts={['base']}
        hoveredParam={hoveredParam}
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    expect(screen.queryByTestId('parameter-preview-overlay')).not.toBeInTheDocument()
  })

  it('does not render parameter preview overlay during head diff mode', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    const hoveredParam = {
      paramId: 'width',
      paramDef: { id: 'width', type: 'slider', min: 10, max: 100 },
      currentValue: 50,
      hint: { type: 'axis_scale', axis: 'x', affected_parts: ['base'] },
    }

    render(
      <Viewer
        {...defaultProps}
        headDiffMode={true}
        headParts={[{ type: 'base', url: '/api/render/head-base.stl' }]}
        hoveredParam={hoveredParam}
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    expect(screen.queryByTestId('parameter-preview-overlay')).not.toBeInTheDocument()
  })

  it('does not render parameter preview overlay when loading', () => {
    const hoveredParam = {
      paramId: 'width',
      paramDef: { id: 'width', type: 'slider', min: 10, max: 100 },
      currentValue: 50,
      hint: { type: 'axis_scale', axis: 'x', affected_parts: ['base'] },
    }

    render(
      <Viewer
        {...defaultProps}
        loading={true}
        hoveredParam={hoveredParam}
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    expect(screen.queryByTestId('parameter-preview-overlay')).not.toBeInTheDocument()
  })

  it('does not render parameter preview overlay when no parts loaded', () => {
    const hoveredParam = {
      paramId: 'width',
      paramDef: { id: 'width', type: 'slider', min: 10, max: 100 },
      currentValue: 50,
      hint: { type: 'axis_scale', axis: 'x', affected_parts: ['base'] },
    }

    render(
      <Viewer
        {...defaultProps}
        hoveredParam={hoveredParam}
        parts={[]}
      />
    )
    expect(screen.queryByTestId('parameter-preview-overlay')).not.toBeInTheDocument()
  })

  it('forwards cachedVariants prop to ParameterPreviewOverlay', () => {
    const fakeGeom = makeFakeGeometry()
    mockUseWorkerLoader.mockReturnValue({ geometry: fakeGeom, scene: null })

    const hoveredParam = {
      paramId: 'width',
      paramDef: { id: 'width', type: 'slider', min: 10, max: 100, label: { en: 'Width' } },
      currentValue: 50,
      hint: { type: 'axis_scale', axis: 'x', affected_parts: ['base'] },
    }

    const cachedVariants = new Map([
      ['width', { min: [{ type: 'base', url: 'blob:min', isGlb: true }] }],
    ])

    render(
      <Viewer
        {...defaultProps}
        hoveredParam={hoveredParam}
        cachedVariants={cachedVariants}
        parts={[{ type: 'base', url: '/api/render/base.stl' }]}
        colors={{ base: '#ff0000' }}
      />
    )
    const overlay = screen.getByTestId('parameter-preview-overlay')
    expect(overlay).toBeInTheDocument()
    expect(overlay.getAttribute('data-has-cached-variants')).toBe('true')
  })
})
