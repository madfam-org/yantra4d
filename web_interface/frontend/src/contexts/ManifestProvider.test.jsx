import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ManifestProvider, useManifest } from './ManifestProvider'

// Mock fetch so the provider doesn't hit the network
beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('no backend'))))
})

function TestConsumer() {
  const {
    loading, getMode, getParametersForMode, getDefaultParams, getDefaultColors, getLabel,
    getCameraViews, getGroupLabel, getViewerConfig, getEstimateConstants, projectSlug,
  } = useManifest()
  if (loading) return <div data-testid="loading">loading</div>

  const unitMode = getMode('unit')
  const gridParams = getParametersForMode('grid')
  const defaults = getDefaultParams()
  const colors = getDefaultColors()
  const label = getLabel({ name: { en: 'Hello', es: 'Hola' } }, 'name', 'en')
  const stringLabel = getLabel({ name: 'Plain' }, 'name', 'en')
  const missingMode = getMode('nonexistent')
  const cameraViews = getCameraViews()
  const visLabel = getGroupLabel('visibility', 'en')
  const colorsLabel = getGroupLabel('colors', 'es')
  const missingGroup = getGroupLabel('nonexistent', 'en')
  const viewerConfig = getViewerConfig()
  const estimateConstants = getEstimateConstants()

  return (
    <div>
      <span data-testid="unit-id">{unitMode?.id}</span>
      <span data-testid="grid-params">{gridParams.map(p => p.id).join(',')}</span>
      <span data-testid="default-size">{defaults.size}</span>
      <span data-testid="default-color-main">{colors.main}</span>
      <span data-testid="label">{label}</span>
      <span data-testid="string-label">{stringLabel}</span>
      <span data-testid="missing-mode">{missingMode === undefined ? 'undefined' : 'found'}</span>
      <span data-testid="camera-views">{cameraViews.map(v => v.id).join(',')}</span>
      <span data-testid="vis-label">{visLabel}</span>
      <span data-testid="colors-label">{colorsLabel}</span>
      <span data-testid="missing-group">{missingGroup}</span>
      <span data-testid="viewer-default-color">{viewerConfig.default_color}</span>
      <span data-testid="wasm-multiplier">{estimateConstants.wasm_multiplier}</span>
      <span data-testid="warning-threshold">{estimateConstants.warning_threshold_seconds}</span>
      <span data-testid="project-slug">{projectSlug}</span>
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

    expect(screen.getByTestId('unit-id').textContent).toBe('unit')
    expect(screen.getByTestId('default-size').textContent).toBe('20')
    expect(screen.getByTestId('default-color-main').textContent).toBe('#e5e7eb')
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
    expect(viewIds).toEqual(['iso', 'top', 'front', 'right'])
  })

  it('getGroupLabel returns translated group label', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    expect(screen.getByTestId('vis-label').textContent).toBe('Visibility')
    expect(screen.getByTestId('colors-label').textContent).toBe('Colores')
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

    expect(screen.getByTestId('viewer-default-color').textContent).toBe('#e5e7eb')
  })

  it('getEstimateConstants returns extended constants', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    expect(screen.getByTestId('wasm-multiplier').textContent).toBe('3')
    expect(screen.getByTestId('warning-threshold').textContent).toBe('60')
  })

  it('projectSlug is derived from manifest', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    expect(screen.getByTestId('project-slug').textContent).toBe('tablaco')
  })

  it('getParametersForMode filters correctly for grid', async () => {
    render(
      <ManifestProvider>
        <TestConsumer />
      </ManifestProvider>
    )

    await waitFor(() => expect(screen.queryByTestId('loading')).not.toBeInTheDocument())

    const gridParamIds = screen.getByTestId('grid-params').textContent.split(',')
    expect(gridParamIds).toContain('rows')
    expect(gridParamIds).toContain('cols')
    expect(gridParamIds).not.toContain('size')
  })
})
