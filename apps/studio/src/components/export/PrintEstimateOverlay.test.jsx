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

  it('renders nothing when volume is negative', () => {
    const { container } = renderWithProviders(
      <PrintEstimateOverlay volumeMm3={-100} boundingBox={{ width: 10, depth: 10, height: 10 }} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when volume is undefined', () => {
    const { container } = renderWithProviders(
      <PrintEstimateOverlay boundingBox={{ width: 10, depth: 10, height: 10 }} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when volume is valid but boundingBox is null', () => {
    const { container } = renderWithProviders(
      <PrintEstimateOverlay volumeMm3={5000} boundingBox={null} />
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

  it('updates estimate when infill changes', () => {
    renderWithProviders(
      <PrintEstimateOverlay volumeMm3={10000} boundingBox={{ width: 30, depth: 30, height: 20 }} />
    )
    const infillSelect = screen.getByLabelText('Infill:')
    // Get initial cost
    const costRowBefore = screen.getByText('Cost:').closest('div')
    const costBefore = costRowBefore.textContent

    fireEvent.change(infillSelect, { target: { value: '1' } })
    expect(infillSelect.value).toBe('1')

    // Cost should increase with 100% infill
    const costRowAfter = screen.getByText('Cost:').closest('div')
    const costAfter = costRowAfter.textContent
    expect(costAfter).not.toBe(costBefore)
  })

  it('shows hours in time when volume is large enough', () => {
    // Use a very large volume and bounding box to produce hours > 0
    renderWithProviders(
      <PrintEstimateOverlay volumeMm3={5000000} boundingBox={{ width: 300, depth: 300, height: 200 }} />
    )
    const timeRow = screen.getByText('Time:').closest('div')
    expect(timeRow.textContent).toMatch(/\d+h\s+\d+m/)
  })

  describe('inline mode', () => {
    it('renders as inline panel with role=status', () => {
      renderWithProviders(
        <PrintEstimateOverlay
          inline
          volumeMm3={5000}
          boundingBox={{ width: 20, depth: 20, height: 15 }}
        />
      )
      const panel = screen.getByRole('status', { name: 'Print estimate' })
      expect(panel).toBeInTheDocument()
      // Inline mode uses p-3 class, not absolute positioning
      expect(panel.className).toContain('p-3')
      expect(panel.className).not.toContain('absolute')
    })

    it('shows material and infill selectors in inline mode', () => {
      renderWithProviders(
        <PrintEstimateOverlay
          inline
          volumeMm3={5000}
          boundingBox={{ width: 20, depth: 20, height: 15 }}
        />
      )
      expect(screen.getByLabelText('Material:')).toBeInTheDocument()
      expect(screen.getByLabelText('Infill:')).toBeInTheDocument()
    })

    it('changes material in inline mode', () => {
      renderWithProviders(
        <PrintEstimateOverlay
          inline
          volumeMm3={5000}
          boundingBox={{ width: 20, depth: 20, height: 15 }}
        />
      )
      const materialSelect = screen.getByLabelText('Material:')
      fireEvent.change(materialSelect, { target: { value: 'petg' } })
      expect(materialSelect.value).toBe('petg')
    })

    it('changes infill in inline mode', () => {
      renderWithProviders(
        <PrintEstimateOverlay
          inline
          volumeMm3={5000}
          boundingBox={{ width: 20, depth: 20, height: 15 }}
        />
      )
      const infillSelect = screen.getByLabelText('Infill:')
      fireEvent.change(infillSelect, { target: { value: '0.5' } })
      expect(infillSelect.value).toBe('0.5')
    })

    it('does not show "Total" label when no per-part data', () => {
      renderWithProviders(
        <PrintEstimateOverlay
          inline
          volumeMm3={5000}
          boundingBox={{ width: 20, depth: 20, height: 15 }}
        />
      )
      expect(screen.queryByText('Total')).not.toBeInTheDocument()
    })
  })

  describe('per-part breakdown', () => {
    const perPartData = {
      base: {
        volumeMm3: 3000,
        boundingBox: { width: 20, depth: 20, height: 5 },
      },
      lid: {
        volumeMm3: 2000,
        boundingBox: { width: 20, depth: 20, height: 10 },
      },
    }

    it('shows "Total" label when per-part data has multiple parts (inline)', () => {
      renderWithProviders(
        <PrintEstimateOverlay
          inline
          volumeMm3={5000}
          boundingBox={{ width: 20, depth: 20, height: 15 }}
          perPartData={perPartData}
        />
      )
      expect(screen.getByText('Total')).toBeInTheDocument()
    })

    it('shows "Per Part" breakdown toggle (inline)', () => {
      renderWithProviders(
        <PrintEstimateOverlay
          inline
          volumeMm3={5000}
          boundingBox={{ width: 20, depth: 20, height: 15 }}
          perPartData={perPartData}
        />
      )
      const toggle = screen.getByText('Per Part')
      expect(toggle).toBeInTheDocument()
      expect(toggle.closest('button')).toHaveAttribute('aria-expanded', 'false')
    })

    it('expands per-part breakdown on click', () => {
      renderWithProviders(
        <PrintEstimateOverlay
          inline
          volumeMm3={5000}
          boundingBox={{ width: 20, depth: 20, height: 15 }}
          perPartData={perPartData}
        />
      )
      const toggle = screen.getByText('Per Part').closest('button')
      fireEvent.click(toggle)
      expect(toggle).toHaveAttribute('aria-expanded', 'true')
      // Part labels should appear (title-cased from id)
      expect(screen.getByText('Base')).toBeInTheDocument()
      expect(screen.getByText('Lid')).toBeInTheDocument()
    })

    it('collapses per-part breakdown on second click', () => {
      renderWithProviders(
        <PrintEstimateOverlay
          inline
          volumeMm3={5000}
          boundingBox={{ width: 20, depth: 20, height: 15 }}
          perPartData={perPartData}
        />
      )
      const toggle = screen.getByText('Per Part').closest('button')
      fireEvent.click(toggle) // open
      fireEvent.click(toggle) // close
      expect(toggle).toHaveAttribute('aria-expanded', 'false')
      expect(screen.queryByText('Base')).not.toBeInTheDocument()
    })

    it('does not show breakdown when perPartData has only one part', () => {
      const singlePart = {
        base: {
          volumeMm3: 5000,
          boundingBox: { width: 20, depth: 20, height: 15 },
        },
      }
      renderWithProviders(
        <PrintEstimateOverlay
          inline
          volumeMm3={5000}
          boundingBox={{ width: 20, depth: 20, height: 15 }}
          perPartData={singlePart}
        />
      )
      expect(screen.queryByText('Per Part')).not.toBeInTheDocument()
      expect(screen.queryByText('Total')).not.toBeInTheDocument()
    })

    it('filters out parts with zero volume', () => {
      const mixedParts = {
        base: {
          volumeMm3: 3000,
          boundingBox: { width: 20, depth: 20, height: 5 },
        },
        empty_part: {
          volumeMm3: 0,
          boundingBox: { width: 0, depth: 0, height: 0 },
        },
        lid: {
          volumeMm3: 2000,
          boundingBox: { width: 20, depth: 20, height: 10 },
        },
      }
      renderWithProviders(
        <PrintEstimateOverlay
          inline
          volumeMm3={5000}
          boundingBox={{ width: 20, depth: 20, height: 15 }}
          perPartData={mixedParts}
        />
      )
      const toggle = screen.getByText('Per Part').closest('button')
      fireEvent.click(toggle)
      expect(screen.getByText('Base')).toBeInTheDocument()
      expect(screen.getByText('Lid')).toBeInTheDocument()
      // empty_part should be filtered out (volume = 0)
      expect(screen.queryByText('Empty Part')).not.toBeInTheDocument()
    })

    it('filters out parts with null boundingBox', () => {
      const mixedParts = {
        base: {
          volumeMm3: 3000,
          boundingBox: { width: 20, depth: 20, height: 5 },
        },
        broken: {
          volumeMm3: 1000,
          boundingBox: null,
        },
        lid: {
          volumeMm3: 2000,
          boundingBox: { width: 20, depth: 20, height: 10 },
        },
      }
      renderWithProviders(
        <PrintEstimateOverlay
          inline
          volumeMm3={5000}
          boundingBox={{ width: 20, depth: 20, height: 15 }}
          perPartData={mixedParts}
        />
      )
      const toggle = screen.getByText('Per Part').closest('button')
      fireEvent.click(toggle)
      expect(screen.getByText('Base')).toBeInTheDocument()
      expect(screen.getByText('Lid')).toBeInTheDocument()
      expect(screen.queryByText('Broken')).not.toBeInTheDocument()
    })
  })

  describe('overlay (non-inline) mode', () => {
    it('renders with absolute positioning by default', () => {
      renderWithProviders(
        <PrintEstimateOverlay
          volumeMm3={5000}
          boundingBox={{ width: 20, depth: 20, height: 15 }}
        />
      )
      const panel = screen.getByRole('status', { name: 'Print estimate' })
      expect(panel.className).toContain('absolute')
    })

    it('shows hours in overlay mode for large volumes', () => {
      renderWithProviders(
        <PrintEstimateOverlay
          volumeMm3={5000000}
          boundingBox={{ width: 300, depth: 300, height: 200 }}
        />
      )
      const timeRow = screen.getByText('Time:').closest('div')
      expect(timeRow.textContent).toMatch(/\d+h\s+\d+m/)
    })

    it('omits hours display when hours is 0', () => {
      // Small volume should produce 0 hours
      renderWithProviders(
        <PrintEstimateOverlay
          volumeMm3={100}
          boundingBox={{ width: 5, depth: 5, height: 5 }}
        />
      )
      const timeRow = screen.getByText('Time:').closest('div')
      // Should show only minutes, no "h" prefix
      expect(timeRow.textContent).not.toMatch(/\d+h/)
      expect(timeRow.textContent).toMatch(/\d+m/)
    })
  })

  // --- Inline layout, currency and time formatting -------------------------
  // The overlay renders a second, inline layout used by the studio's estimate
  // strip; none of it was covered, nor the currency toggle or the hours branch
  // of the time row.

  const box = { width: 40, depth: 40, height: 40 }

  it('inline layout renders its own labelled controls', () => {
    renderWithProviders(
      <PrintEstimateOverlay volumeMm3={50000} boundingBox={box} inline />
    )
    // The inline layout uses -inline control ids so it can coexist with the
    // floating one without duplicating DOM ids.
    expect(document.querySelector('#pe-material-inline')).toBeTruthy()
    expect(document.querySelector('#pe-pattern-inline')).toBeTruthy()
    expect(document.querySelector('#pe-nozzle-inline')).toBeTruthy()
  })

  it('changing material in the inline layout keeps the estimate rendered', () => {
    renderWithProviders(
      <PrintEstimateOverlay volumeMm3={50000} boundingBox={box} inline />
    )
    const select = document.querySelector('#pe-material-inline')
    const option = select.querySelectorAll('option')[1]
    if (option) fireEvent.change(select, { target: { value: option.value } })
    expect(screen.getByRole('status', { name: 'Print estimate' })).toBeInTheDocument()
  })

  it('a large volume reports hours as well as minutes', () => {
    renderWithProviders(
      <PrintEstimateOverlay volumeMm3={5_000_000} boundingBox={{ width: 200, depth: 200, height: 200 }} />
    )
    // hours > 0 takes the "Nh Mm" branch; small prints render minutes only.
    expect(screen.getByText(/\d+h \d+m/)).toBeInTheDocument()
  })

  it('a small volume reports minutes only', () => {
    renderWithProviders(
      <PrintEstimateOverlay volumeMm3={500} boundingBox={{ width: 10, depth: 10, height: 5 }} />
    )
    expect(screen.queryByText(/\dh \d+m/)).not.toBeInTheDocument()
  })
})

