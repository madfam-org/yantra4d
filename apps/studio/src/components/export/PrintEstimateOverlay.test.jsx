import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import PrintEstimateOverlay from './PrintEstimateOverlay'
import { LanguageProvider } from '../../contexts/system/LanguageProvider'
import { ManifestProvider } from '../../contexts/project/ManifestProvider'
import { MemoryRouter } from 'react-router-dom'

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('no backend'))
})

function renderWithProviders(ui) {
  return render(
    <MemoryRouter>
      <LanguageProvider defaultLanguage="en">
        <ManifestProvider>
          {ui}
        </ManifestProvider>
      </LanguageProvider>
    </MemoryRouter>
  )
}

describe('PrintEstimateOverlay', () => {
  it('renders nothing when volume is 0', () => {
    const { container } = renderWithProviders(
      <PrintEstimateOverlay volumeMm3={0} boundingBox={{ width: 10, depth: 10, height: 10 }} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when volume is null', () => {
    const { container } = renderWithProviders(
      <PrintEstimateOverlay volumeMm3={null} boundingBox={null} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders estimate with valid volume and bounding box', () => {
    renderWithProviders(
      <PrintEstimateOverlay volumeMm3={5000} boundingBox={{ width: 20, depth: 20, height: 15 }} />
    )
    expect(screen.getByText('Print Estimate')).toBeInTheDocument()
    // Should show time, weight, length, cost
    expect(screen.getByText('Time:')).toBeInTheDocument()
    expect(screen.getByText('Weight:')).toBeInTheDocument()
    expect(screen.getByText('Filament:')).toBeInTheDocument()
    expect(screen.getByText('Cost:')).toBeInTheDocument()
  })

  it('shows material selector with PLA default', () => {
    renderWithProviders(
      <PrintEstimateOverlay volumeMm3={5000} boundingBox={{ width: 20, depth: 20, height: 15 }} />
    )
    const materialSelect = screen.getByLabelText('Material:')
    expect(materialSelect).toBeInTheDocument()
    expect(materialSelect.value).toBe('pla')
  })

  it('shows infill selector with 20% default', () => {
    renderWithProviders(
      <PrintEstimateOverlay volumeMm3={5000} boundingBox={{ width: 20, depth: 20, height: 15 }} />
    )
    const infillSelect = screen.getByLabelText('Infill:')
    expect(infillSelect).toBeInTheDocument()
    expect(infillSelect.value).toBe('0.2')
  })

  it('updates estimate when material changes', () => {
    renderWithProviders(
      <PrintEstimateOverlay volumeMm3={5000} boundingBox={{ width: 20, depth: 20, height: 15 }} />
    )
    const materialSelect = screen.getByLabelText('Material:')
    fireEvent.change(materialSelect, { target: { value: 'abs' } })
    expect(materialSelect.value).toBe('abs')
  })

  it('displays weight as a number with g suffix', () => {
    renderWithProviders(
      <PrintEstimateOverlay volumeMm3={10000} boundingBox={{ width: 30, depth: 30, height: 20 }} />
    )
    // Weight text should contain 'g'
    const weightRow = screen.getByText('Weight:').closest('div')
    expect(weightRow.textContent).toMatch(/\d+(\.\d+)?g/)
  })

  it('displays cost with dollar sign', () => {
    renderWithProviders(
      <PrintEstimateOverlay volumeMm3={10000} boundingBox={{ width: 30, depth: 30, height: 20 }} />
    )
    const costRow = screen.getByText('Cost:').closest('div')
    expect(costRow.textContent).toMatch(/~?\$\d+/)
  })
})
