// @vitest-environment jsdom
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ManifestProvider, useManifest } from './ManifestProvider'
import fallbackManifest from '../../config/fallback-manifest'

vi.mock('react-router-dom', () => ({
  useLocation: () => ({ pathname: '/project/gridfinity', hash: '' }),
  useNavigate: () => vi.fn()
}))

// Mock fetch so the provider doesn't hit the network
beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('no backend'))))
})

function TestConsumer() {
  const {
    loading, manifest, getMode, getParametersForMode, getDefaultParams, getDefaultColors, getLabel,
    getCameraViews, getGroupLabel, getViewerConfig, getEstimateConstants, projectSlug,
    projects, switchProject,
  } = useManifest()
  if (loading) return <div data-testid="loading">loading</div>

  const binMode = getMode('bin')
  // The fallback manifest is synced from projects/gridfinity/project.json, which
  // is CadQuery-only since 2026-09-04: modes are `bin` and `baseplate`, and no
  // parameter declares visible_in_modes any more, so every mode sees all ten.
  const baseplateParams = getParametersForMode('baseplate')
  const defaults = getDefaultParams()
  const colors = getDefaultColors()
  const label = getLabel({ name: { en: 'Hello', es: 'Hola' } }, 'name', 'en')
  const stringLabel = getLabel({ name: 'Plain' }, 'name', 'en')
  const missingMode = getMode('nonexistent')
  const cameraViews = getCameraViews()
  const dimLabel = getGroupLabel('dimensions', 'en')
  const mountLabel = getGroupLabel('mounting', 'es')
  const missingGroup = getGroupLabel('nonexistent', 'en')
  const viewerConfig = getViewerConfig()
  const estimateConstants = getEstimateConstants()

  return (
    <div>
      <span data-testid="bin-id">{binMode?.id}</span>
      <span data-testid="baseplate-params">{baseplateParams.map(p => p.id).join(',')}</span>
      <span data-testid="default-grid-x">{defaults.grid_x}</span>
      <span data-testid="default-color-bin">{colors.bin}</span>
      <span data-testid="label">{label}</span>
      <span data-testid="string-label">{stringLabel}</span>
      <span data-testid="missing-mode">{missingMode === undefined ? 'undefined' : 'found'}</span>
      <span data-testid="camera-views">{cameraViews.map(v => v.id).join(',')}</span>
      <span data-testid="dim-label">{dimLabel}</span>
      <span data-testid="mount-label">{mountLabel}</span>
      <span data-testid="missing-group">{missingGroup}</span>
      <span data-testid="viewer-config">{JSON.stringify(viewerConfig)}</span>
      <span data-testid="wasm-multiplier">{estimateConstants.wasm_multiplier}</span>
      <span data-testid="warning-threshold">{estimateConstants.warning_threshold_seconds}</span>
      <span data-testid="project-slug">{projectSlug}</span>
      <span data-testid="projects-count">{projects.length}</span>
      <span data-testid="export-formats">{JSON.stringify(manifest?.export_formats || 'undefined')}</span>
      <span data-testid="print-estimation">{JSON.stringify(manifest?.print_estimation || 'undefined')}</span>
      <button data-testid="switch-btn" onClick={() => switchProject('other')}>switch</button>
    </div>
  )
}

describe('ManifestProvider', () => {
  it('provides fallback manifest data', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    expect(screen.getByTestId('bin-id').textContent).toBe('bin')
    expect(screen.getByTestId('default-grid-x').textContent).toBe('2')
    expect(screen.getByTestId('default-color-bin').textContent).toBe('#4a90d9')
    expect(screen.getByTestId('label').textContent).toBe('Hello')
    expect(screen.getByTestId('string-label').textContent).toBe('Plain')
    expect(screen.getByTestId('missing-mode').textContent).toBe('undefined')
  })

  it('getCameraViews returns views from manifest', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    const viewIds = screen.getByTestId('camera-views').textContent.split(',')
    expect(viewIds).toEqual(['iso', 'top', 'front'])
  })

  it('getGroupLabel returns translated group label', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    expect(screen.getByTestId('dim-label').textContent).toBe('Dimensions')
    expect(screen.getByTestId('mount-label').textContent).toBe('Montaje')
  })

  it('getGroupLabel returns groupId for unknown groups', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    expect(screen.getByTestId('missing-group').textContent).toBe('nonexistent')
  })

  it('getViewerConfig returns viewer settings', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    // The dual-kernel Gridfinity fallback manifest omits the `viewer` block, so the
    // accessor falls back to an empty object (consumers apply their own defaults).
    expect(screen.getByTestId('viewer-config').textContent).toBe('{}')
  })

  it('getEstimateConstants returns extended constants', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    expect(screen.getByTestId('wasm-multiplier').textContent).toBe('4')
    expect(screen.getByTestId('warning-threshold').textContent).toBe('90')
  })

  it('projectSlug is derived from manifest', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    expect(screen.getByTestId('project-slug').textContent).toBe('gridfinity')
  })

  it('getParametersForMode filters correctly for baseplate', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    const baseplateParamIds = screen.getByTestId('baseplate-params').textContent.split(',')
    // width_units/depth_units/height_units were the OpenSCAD trio, scoped by
    // visible_in_modes; they left with the OpenSCAD modes. Nothing in the
    // cartridge declares visible_in_modes now, so the filter is a pass-through
    // and every parameter reaches every mode — assert that, not a stale scope.
    expect(baseplateParamIds).toContain('bp_thickness')
    expect(baseplateParamIds).toContain('grid_x')
    expect(baseplateParamIds).not.toContain('width_units')
  })

  it('projects list is empty when fetch fails (fallback mode)', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    expect(screen.getByTestId('projects-count').textContent).toBe('0')
  })

  it('exposes switchProject function', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    // switchProject should be callable without error
    const btn = screen.getByTestId('switch-btn')
    expect(btn).toBeInTheDocument()
  })

  it('export_formats from fallback manifest and print_estimation undefined', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    // Gridfinity fallback manifest includes export_formats but not print_estimation
    expect(screen.getByTestId('export-formats').textContent).toBe('["stl","3mf","step","glb","gltf","obj"]')
    expect(screen.getByTestId('print-estimation').textContent).toBe('"undefined"')
  })

  it('fetches projects list from /api/projects on mount', async () => {
    const projectsList = [
      { slug: 'gridfinity', name: 'Gridfinity Extended', version: '1.0.0' },
      { slug: 'portacosas', name: 'Portacosas', version: '1.0.0' },
      { slug: 'ultimate-box', name: 'Ultimate Box', version: '0.1.0' },
      { slug: 'keyv2', name: 'KeyV2', version: '0.1.0' },
      { slug: 'multiboard', name: 'Multiboard', version: '0.1.0' },
      { slug: 'fasteners', name: 'Fasteners', version: '0.1.0' },
      { slug: 'gears', name: 'Gears', version: '0.1.0' },
      { slug: 'yapp-box', name: 'YAPP Box', version: '0.1.0' },
      { slug: 'stemfie', name: 'STEMFIE', version: '0.1.0' },
      { slug: 'polydice', name: 'Polydice', version: '0.1.0' },
      { slug: 'julia-vase', name: 'Julia Vase', version: '0.1.0' },
      { slug: 'voronoi', name: 'Voronoi Generator', version: '0.1.0' },
      { slug: 'maze', name: 'Maze Generator', version: '0.1.0' },
      { slug: 'relief', name: 'Text Relief Generator', version: '0.1.0' },
    ]

    const fetchMock = vi.fn()
    // First call: /api/projects
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(projectsList),
    })
    // Second call: /api/projects/gridfinity/manifest
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(fallbackManifest),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    expect(fetchMock.mock.calls[0][0]).toContain('/api/projects')
    expect(screen.getByTestId('projects-count').textContent).toBe('14')
    expect(screen.getByTestId('project-slug').textContent).toBe('gridfinity')
  })
})
