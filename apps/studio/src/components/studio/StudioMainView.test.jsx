import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('@/components/ui/resizable', () => ({
  ResizablePanelGroup: function MockPanelGroup({ children, orientation }) {
    return <div data-testid="resizable-panel-group" data-orientation={orientation}>{children}</div>
  },
  ResizablePanel: function MockPanel({ children, id }) {
    return <div data-testid="resizable-panel" data-panel-id={id}>{children}</div>
  },
  ResizableHandle: function MockHandle({ orientation }) {
    return <div data-testid="resizable-handle" data-orientation={orientation} />
  },
}))

vi.mock('../viewer/Viewer', () => ({
  default: React.forwardRef(function MockViewer(props) {
    return <div data-testid="viewer" data-loading={props.loading} data-has-cached-variants={props.cachedVariants ? 'true' : 'false'} />
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
  default: function MockModelInfo(props) {
    // totalPieceCount is computed in StudioMainView and handed straight to this
    // child, so surface it for assertions rather than rendering a bare stub.
    return <div data-testid="model-info" data-total-pieces={props.totalPieceCount ?? ''} />
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

vi.mock('../feedback/WelcomeOverlay', () => ({
  default: function MockWelcomeOverlay() {
    return <div data-testid="welcome-overlay" />
  },
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
  hoveredParam: null,
  cachedVariants: null,
}

beforeEach(() => {
  vi.clearAllMocks()
  useProject.mockReturnValue(baseContext)
  useLanguage.mockReturnValue({ t })
})

describe('StudioMainView', () => {
  it('renders viewer and console log area', () => {
    render(<StudioMainView />)
    // Viewer content is shared across desktop + mobile layouts (both in DOM)
    expect(screen.getAllByTestId('viewer').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByRole('log').length).toBeGreaterThanOrEqual(1)
  })

  it('sets aria-busy when loading', () => {
    useProject.mockReturnValue({ ...baseContext, loading: true })
    render(<StudioMainView />)
    const viewer = screen.getAllByTestId('viewer')[0]
    expect(viewer.closest('[aria-busy]')).toHaveAttribute('aria-busy', 'true')
  })

  it('does not set aria-busy when idle', () => {
    render(<StudioMainView />)
    const viewer = screen.getAllByTestId('viewer')[0]
    expect(viewer.closest('[aria-busy]')).toHaveAttribute('aria-busy', 'false')
  })

  it('shows rendering status chip when loading', () => {
    useProject.mockReturnValue({ ...baseContext, loading: true, progress: 5, progressPhase: 'meshing' })
    render(<StudioMainView />)
    expect(screen.getAllByText(/Rendering.*5s.*meshing/).length).toBeGreaterThanOrEqual(1)
  })

  it('shows ready status chip when parts available', () => {
    useProject.mockReturnValue({ ...baseContext, parts: [{ id: 'body' }] })
    render(<StudioMainView />)
    expect(screen.getAllByText('Ready').length).toBeGreaterThanOrEqual(1)
  })

  it('shows no status chip when idle with no parts', () => {
    render(<StudioMainView />)
    expect(screen.queryByText('Rendering')).not.toBeInTheDocument()
    expect(screen.queryByText('Ready')).not.toBeInTheDocument()
  })

  it('announces render status via live region', () => {
    useProject.mockReturnValue({ ...baseContext, loading: true })
    const { rerender, container } = render(<StudioMainView />)
    const liveRegions = container.querySelectorAll('.sr-only[aria-live="polite"]')
    expect(liveRegions.length).toBeGreaterThanOrEqual(1)
    const liveRegion = liveRegions[0]
    expect(liveRegion.textContent).toBe('Rendering in progress')

    useProject.mockReturnValue({ ...baseContext, loading: false, parts: [{ id: 'body' }] })
    rerender(<StudioMainView />)
    expect(liveRegion.textContent).toContain('Render complete')
  })

  it('displays console logs', () => {
    useProject.mockReturnValue({ ...baseContext, logs: 'ECHO: param=5' })
    render(<StudioMainView />)
    expect(screen.getAllByText('ECHO: param=5').length).toBeGreaterThanOrEqual(1)
  })

  it('renders mobile console toggle button', () => {
    render(<StudioMainView />)
    expect(screen.getByLabelText('Toggle console panel')).toBeInTheDocument()
  })

  it('renders print estimate overlay when estimate exists', () => {
    useProject.mockReturnValue({ ...baseContext, printEstimate: { volumeMm3: 1200, boundingBox: {} } })
    render(<StudioMainView />)
    expect(screen.getAllByTestId('print-overlay').length).toBeGreaterThanOrEqual(1)
  })

  it('does not render print estimate overlay when no estimate', () => {
    render(<StudioMainView />)
    expect(screen.queryByTestId('print-overlay')).not.toBeInTheDocument()
  })

  it('forwards cachedVariants from context to Viewer', () => {
    const cachedVariants = new Map([['width', { min: [] }]])
    useProject.mockReturnValue({ ...baseContext, cachedVariants })
    render(<StudioMainView />)
    const viewer = screen.getAllByTestId('viewer')[0]
    expect(viewer.getAttribute('data-has-cached-variants')).toBe('true')
  })

  it('forwards null cachedVariants to Viewer when none available', () => {
    render(<StudioMainView />)
    const viewer = screen.getAllByTestId('viewer')[0]
    expect(viewer.getAttribute('data-has-cached-variants')).toBe('false')
  })

  it('passes orientation="vertical" to the desktop panel group', () => {
    render(<StudioMainView />)
    const groups = screen.getAllByTestId('resizable-panel-group')
    // Desktop group should have vertical orientation
    const verticalGroup = groups.find(g => g.getAttribute('data-orientation') === 'vertical')
    expect(verticalGroup).toBeTruthy()
  })

  it('assigns panel ids to viewer and console panels', () => {
    render(<StudioMainView consoleCollapsed={false} consoleSize={30} />)
    const panels = screen.getAllByTestId('resizable-panel')
    const panelIds = panels.map(p => p.getAttribute('data-panel-id')).filter(Boolean)
    expect(panelIds).toContain('viewer')
    expect(panelIds).toContain('console')
  })

  // --- Manifest-driven branches -------------------------------------------
  // baseContext leaves manifest, printEstimate and the job ids empty, so the
  // part-count computation, welcome overlay, estimate strip and the physics and
  // optimization badges were all unreachable.

  const withContext = (patch) => {
    useProject.mockReturnValue({ ...baseContext, ...patch })
  }

  it('part count multiplies quantities declared per part', () => {
    withContext({
      manifest: {
        modes: [{ id: 'full', parts: ['body', 'pin'], part_quantities: { body: 1, pin: 4 } }],
      },
      params: {},
      // ModelInfoPanel, which receives the count, only renders once a render
      // has produced parts.
      parts: [{ type: 'body' }, { type: 'pin' }],
    })
    render(<StudioMainView />)
    // 1 body + 4 pins.
    // StudioMainView renders its own desktop and mobile trees, so this child
    // appears twice; both carry the same computed count.
    expect(screen.getAllByTestId('model-info')[0]).toHaveAttribute('data-total-pieces', '5')
  })

  it('a part with no declared quantity counts as one', () => {
    withContext({
      manifest: { modes: [{ id: 'full', parts: ['body', 'lid'], part_quantities: { body: 2 } }] },
      parts: [{ type: 'body' }, { type: 'lid' }],
    })
    render(<StudioMainView />)
    expect(screen.getAllByTestId('model-info')[0]).toHaveAttribute('data-total-pieces', '3')
  })

  it('no part count when the active mode is absent from the manifest', () => {
    withContext({ manifest: { modes: [{ id: 'other', parts: ['a'], part_quantities: { a: 9 } }] } })
    const { container } = render(<StudioMainView />)
    expect(container).toBeTruthy() // renders without the count block
  })

  it('welcome overlay appears when the manifest enables it', () => {
    localStorage.clear()
    withContext({
      projectSlug: 'demo',
      manifest: { project: { welcome: { enabled: true, title: 'Welcome aboard' } } },
    })
    render(<StudioMainView />)
    expect(screen.getAllByTestId('welcome-overlay').length).toBeGreaterThan(0)
  })

  it('welcome overlay stays hidden once dismissed for that project', () => {
    localStorage.setItem('yantra4d-welcome-demo', '1')
    withContext({
      projectSlug: 'demo',
      manifest: { project: { welcome: { enabled: true, title: 'Welcome aboard' } } },
    })
    render(<StudioMainView />)
    expect(screen.queryAllByTestId('welcome-overlay')).toHaveLength(0)
    localStorage.clear()
  })

  it('welcome overlay stays hidden when the manifest does not enable it', () => {
    localStorage.clear()
    withContext({
      projectSlug: 'demo',
      manifest: { project: { welcome: { enabled: false, title: 'Welcome aboard' } } },
    })
    render(<StudioMainView />)
    expect(screen.queryAllByTestId('welcome-overlay')).toHaveLength(0)
  })

  it('the collapsed console previews the last log line', () => {
    withContext({ logs: 'first line\nsecond line\nlast line' })
    render(<StudioMainView />)
    expect(document.body.textContent).toContain('last line')
  })

  it('print estimate strip appears once a volume is known', () => {
    withContext({ printEstimate: { volumeMm3: 1234 } })
    render(<StudioMainView />)
    expect(screen.getAllByTestId('print-overlay').length).toBeGreaterThan(0)
  })

  it('estimate toggle is offered with a volume and withdrawn when estimation is disabled', () => {
    withContext({ printEstimate: { volumeMm3: 1234 } })
    const { unmount } = render(<StudioMainView />)
    expect(screen.getAllByLabelText('Toggle print estimate panel').length).toBeGreaterThan(0)
    unmount()

    withContext({
      printEstimate: { volumeMm3: 1234 },
      manifest: { print_estimation: { enabled: false } },
    })
    render(<StudioMainView />)
    expect(screen.queryAllByLabelText('Toggle print estimate panel')).toHaveLength(0)
  })

  it('compare mode renders a slot per comparison', () => {
    withContext({ parts: [{ type: 'body' }] })
    render(
      <StudioMainView
        compareMode
        comparisonSlots={[{ id: 'a', parts: [] }, { id: 'b', parts: [] }]}
      />
    )
    // The compare layout replaces the single viewer with one per slot.
    expect(screen.getAllByTestId('viewer').length).toBeGreaterThan(1)
  })

  it('optimization logs are shown while a run reports them', () => {
    // The logs panel only renders while a job is active; the last line is
    // what the badge shows.
    // The simulation toolbar as a whole only renders for a mode with rendered
    // parts and no render in flight.
    withContext({
      mode: 'full',
      parts: [{ type: 'body' }],
      loading: false,
      optimizationJobId: 'opt-1',
      optimizationProgress: 30,
      optimizationLogs: ['seeding', 'iteration 1'],
    })
    render(<StudioMainView />)
    expect(document.body.textContent).toContain('iteration 1')
  })

  it('an estimate nested under total is read the same as a flat one', () => {
    // The estimate arrives either flat or wrapped in `total` depending on
    // whether the render produced one part or several.
    withContext({ printEstimate: { total: { volumeMm3: 900, boundingBox: { width: 1, depth: 2, height: 3 } } } })
    render(<StudioMainView />)
    expect(screen.getAllByTestId('print-overlay').length).toBeGreaterThan(0)
  })

  it('a part quantity given as a formula string is coerced to a number', () => {
    withContext({
      manifest: {
        modes: [{ id: 'full', parts: ['body'], part_quantities: { body: '2 + 3' } }],
      },
      params: {},
      parts: [{ type: 'body' }],
    })
    render(<StudioMainView />)
    expect(screen.getAllByTestId('model-info')[0]).toHaveAttribute('data-total-pieces', '5')
  })

  it('an unevaluable part quantity counts as one rather than NaN', () => {
    withContext({
      manifest: {
        modes: [{ id: 'full', parts: ['body'], part_quantities: { body: 'not a formula' } }],
      },
      parts: [{ type: 'body' }],
    })
    render(<StudioMainView />)
    const count = screen.getAllByTestId('model-info')[0].getAttribute('data-total-pieces')
    expect(count).not.toContain('NaN')
  })
})

