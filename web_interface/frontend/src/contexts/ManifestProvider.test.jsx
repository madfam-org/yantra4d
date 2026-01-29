import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ManifestProvider, useManifest } from './ManifestProvider'

// Mock fetch so the provider doesn't hit the network
beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('no backend'))))
})

function TestConsumer() {
  const { loading, getMode, getParametersForMode, getDefaultParams, getDefaultColors, getLabel } = useManifest()
  if (loading) return <div data-testid="loading">loading</div>

  const unitMode = getMode('unit')
  const gridParams = getParametersForMode('grid')
  const defaults = getDefaultParams()
  const colors = getDefaultColors()
  const label = getLabel({ name: { en: 'Hello', es: 'Hola' } }, 'name', 'en')
  const stringLabel = getLabel({ name: 'Plain' }, 'name', 'en')
  const missingMode = getMode('nonexistent')

  return (
    <div>
      <span data-testid="unit-id">{unitMode?.id}</span>
      <span data-testid="grid-params">{gridParams.map(p => p.id).join(',')}</span>
      <span data-testid="default-size">{defaults.size}</span>
      <span data-testid="default-color-main">{colors.main}</span>
      <span data-testid="label">{label}</span>
      <span data-testid="string-label">{stringLabel}</span>
      <span data-testid="missing-mode">{missingMode === undefined ? 'undefined' : 'found'}</span>
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
