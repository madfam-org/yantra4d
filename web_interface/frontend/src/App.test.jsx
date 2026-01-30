import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import App from './App'
import { renderWithProviders } from './test/render-with-providers'

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
    expect(screen.getByText('Tablaco Studio')).toBeInTheDocument()
  })

  it('renders mode tabs for all manifest modes', () => {
    renderApp()
    expect(screen.getByText('Unit')).toBeInTheDocument()
    expect(screen.getByText('Assembly')).toBeInTheDocument()
    expect(screen.getByText('Grid')).toBeInTheDocument()
  })

  it('all mode tabs render as interactive tab elements', () => {
    renderApp()
    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(3)
    expect(tabs[0]).toHaveTextContent('Unit')
    expect(tabs[1]).toHaveTextContent('Assembly')
    expect(tabs[2]).toHaveTextContent('Grid')
    // Unit tab is selected by default
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

  it('verify button calls verify after parts are loaded', async () => {
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

  it('language toggle switches en to es', async () => {
    renderApp()
    const langBtn = screen.getByTitle('Español')
    fireEvent.click(langBtn)
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
})
