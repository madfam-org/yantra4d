import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import App from './App'
import { renderWithProviders } from './test/render-with-providers'
import fallbackManifest from './config/fallback-manifest.json'

expect.extend(toHaveNoViolations)

// Mock services
vi.mock('./services/renderService', () => ({
  renderParts: vi.fn(() => Promise.resolve([{ type: 'main', url: 'blob:mock-url', blob: new Blob() }])),
  cancelRender: vi.fn(() => Promise.resolve()),
  estimateRenderTime: vi.fn(() => 10),
  getRenderMode: vi.fn(() => 'detecting'),
}))

vi.mock('./services/verifyService', () => ({
  verify: vi.fn(() => Promise.resolve({ status: 'passed', passed: true, output: 'All checks passed', parts_checked: 1 })),
}))

// Mock Viewer (WebGL not available in jsdom)
vi.mock('./components/Viewer', () => ({
  // eslint-disable-next-line no-unused-vars
  default: React.forwardRef(function MockViewer(props, ref) { return <div data-testid="viewer-mock">Viewer Mock</div> }),
}))

// Mock fetch for ManifestProvider
beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('no backend'))
  localStorage.clear()
})

function renderApp() {
  return renderWithProviders(<App />)
}

describe('App', () => {
  it('renders header with project name', () => {
    renderApp()
    expect(screen.getByText(fallbackManifest.project.name)).toBeInTheDocument()
  })

  it('renders mode tabs for all manifest modes', () => {
    renderApp()
    for (const mode of fallbackManifest.modes) {
      const matches = screen.getAllByText(mode.label.en)
      expect(matches.length).toBeGreaterThanOrEqual(1)
    }
  })

  it('all mode tabs render as interactive tab elements', () => {
    renderApp()
    const tabs = screen.getAllByRole('tab')
    // Desktop sidebar + mobile bar each render mode tabs
    const modeCount = fallbackManifest.modes.length
    expect(tabs.length).toBeGreaterThanOrEqual(modeCount)
    // Check that each mode label appears at least once
    fallbackManifest.modes.forEach((mode) => {
      expect(screen.getAllByText(mode.label.en).length).toBeGreaterThanOrEqual(1)
    })
    // First tab is selected by default
    expect(tabs[0]).toHaveAttribute('aria-selected', 'true')
  })

  it('generate button calls renderParts', async () => {
    const { renderParts } = await import('./services/renderService')
    renderApp()
    const genButton = screen.getByText('Generate')
    fireEvent.click(genButton)
    await waitFor(() => {
      expect(renderParts).toHaveBeenCalled()
    })
  })

  it('verify button calls verify with project slug after parts are loaded', async () => {
    const { verify } = await import('./services/verifyService')
    renderApp()

    // Generate to get parts
    fireEvent.click(screen.getByText('Generate'))

    // Wait for loading to finish and verify button to become enabled
    await waitFor(() => {
      const verifyBtn = screen.getByText('Run Verification Suite')
      expect(verifyBtn).not.toBeDisabled()
    })

    fireEvent.click(screen.getByText('Run Verification Suite'))
    await waitFor(() => {
      expect(verify).toHaveBeenCalled()
      // verify is now called with (parts, mode, projectSlug)
      const lastCall = verify.mock.calls[verify.mock.calls.length - 1]
      expect(lastCall).toHaveLength(3)
      expect(lastCall[2]).toBe('tablaco') // projectSlug from fallback manifest
    })
  })

  it('reset button restores default params', async () => {
    renderApp()
    const resetBtn = screen.getByText('Reset to Defaults')
    fireEvent.click(resetBtn)
    // After reset, slider values should show defaults — check size=20
    expect(screen.getByText('20')).toBeInTheDocument()
  })

  it('long render estimate shows ConfirmRenderDialog', async () => {
    const { estimateRenderTime } = await import('./services/renderService')
    estimateRenderTime.mockReturnValue(120) // > 60s threshold

    renderApp()
    fireEvent.click(screen.getByText('Generate'))

    await waitFor(() => {
      expect(screen.getByText(/estimated/i)).toBeInTheDocument()
    })
  })

  it('language selector switches en to es', async () => {
    renderApp()
    // Click Globe button to open language dropdown
    const langBtn = screen.getByTitle('Toggle Language')
    fireEvent.click(langBtn)
    // Click Español in the dropdown
    const esOption = screen.getByText('Español')
    fireEvent.click(esOption)
    await waitFor(() => {
      expect(screen.getByText('Generar')).toBeInTheDocument()
    })
  })

  it('download STL button is disabled when no parts', () => {
    renderApp()
    const dlBtn = screen.getByText(/Download STL/i)
    expect(dlBtn).toBeDisabled()
  })

  it('theme toggle shows translated tooltip', () => {
    renderApp()
    // renderWithProviders defaults to theme='light'
    const themeBtn = screen.getByTitle('Theme: Light')
    expect(themeBtn).toBeInTheDocument()
    fireEvent.click(themeBtn)
    // After click, theme cycles light → dark
    expect(screen.getByTitle('Theme: Dark')).toBeInTheDocument()
  })

  it('has no a11y violations', { timeout: 15000 }, async () => {
    const { container } = renderApp()
    const results = await axe(container, {
      rules: {
        // Radix UI tabs render aria-controls referencing panels not yet in DOM
        'aria-valid-attr-value': { enabled: false },
      },
    })
    expect(results).toHaveNoViolations()
  })

  it('sets 3-segment URL hash with project slug', () => {
    renderApp()
    const hash = window.location.hash
    // Hash should now be #/{projectSlug}/{presetId}/{modeId}
    const segments = hash.replace(/^#\/?/, '').split('/').filter(Boolean)
    expect(segments.length).toBe(3)
    expect(segments[0]).toBe('tablaco') // project slug
  })

  it('renders share button', () => {
    renderApp()
    expect(screen.getByTitle('Share configuration')).toBeInTheDocument()
  })

  it('renders undo and redo buttons', () => {
    renderApp()
    expect(screen.getByTitle('Undo')).toBeInTheDocument()
    expect(screen.getByTitle('Redo')).toBeInTheDocument()
  })

  it('undo button is disabled initially (no history)', () => {
    renderApp()
    expect(screen.getByTitle('Undo')).toBeDisabled()
  })

  it('redo button is disabled initially (no future)', () => {
    renderApp()
    expect(screen.getByTitle('Redo')).toBeDisabled()
  })

  it('studio view renders "powered by Yantra4D" tagline', () => {
    renderApp()
    expect(screen.getByText('powered by Yantra4D')).toBeInTheDocument()
  })
})
