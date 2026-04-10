import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({ t: (key) => key }),
}))

vi.mock('../../hooks/system/useUnitSystem', () => ({
  useUnitSystem: () => ({
    format: (v) => `${v.toFixed(1)}mm`,
    formatVolume: (v, p = 0) => `${v.toFixed(p)} mm³`,
    label: 'mm',
  }),
}))

import ModelInfoPanel from './ModelInfoPanel'

describe('ModelInfoPanel', () => {
  it('returns null when no data', () => {
    const { container } = render(<ModelInfoPanel printEstimate={null} partCount={0} />)
    expect(container.innerHTML).toBe('')
  })

  it('returns null when volume is zero and no bounding box', () => {
    const estimate = { total: { volumeMm3: 0 } }
    const { container } = render(<ModelInfoPanel printEstimate={estimate} partCount={0} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders title and volume', () => {
    const estimate = {
      total: {
        volumeMm3: 12345,
        boundingBox: { width: 50, depth: 30, height: 20 },
      },
    }
    render(<ModelInfoPanel printEstimate={estimate} partCount={1} />)
    expect(screen.getByText('info.title')).toBeInTheDocument()
    // Volume formatted as vol.toFixed(0) + label³ → "12345 mm³"
    expect(screen.getByText('12345 mm³')).toBeInTheDocument()
  })

  it('renders triangle count when provided via estimate', () => {
    const estimate = {
      total: {
        volumeMm3: 100,
        boundingBox: { width: 10, depth: 10, height: 10 },
        triangleCount: 5000,
      },
    }
    render(<ModelInfoPanel printEstimate={estimate} partCount={1} />)
    // triangleCount.toLocaleString() → "5,000" in en-US
    expect(screen.getByText('5,000')).toBeInTheDocument()
  })

  it('renders triangle count when provided via prop', () => {
    const estimate = {
      total: {
        volumeMm3: 100,
        boundingBox: { width: 10, depth: 10, height: 10 },
      },
    }
    render(<ModelInfoPanel printEstimate={estimate} partCount={1} triangleCount={3000} />)
    expect(screen.getByText('3,000')).toBeInTheDocument()
  })

  it('renders part count and total pieces', () => {
    const estimate = {
      total: {
        volumeMm3: 100,
        boundingBox: { width: 10, depth: 10, height: 10 },
      },
    }
    render(<ModelInfoPanel printEstimate={estimate} partCount={3} totalPieceCount={12} />)
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('info.part_types')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('info.total_pieces')).toBeInTheDocument()
  })

  it('hides total pieces when equal to part count', () => {
    const estimate = {
      total: {
        volumeMm3: 100,
        boundingBox: { width: 10, depth: 10, height: 10 },
      },
    }
    render(<ModelInfoPanel printEstimate={estimate} partCount={1} totalPieceCount={1} />)
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.queryByText('info.total_pieces')).not.toBeInTheDocument()
  })

  it('renders formatted dimensions', () => {
    const estimate = {
      total: {
        volumeMm3: 100,
        boundingBox: { width: 50, depth: 30, height: 20 },
      },
    }
    render(<ModelInfoPanel printEstimate={estimate} partCount={1} />)
    // formatDim(50) → "50.0mm", formatDim(30) → "30.0mm", formatDim(20) → "20.0mm"
    expect(screen.getByText('info.dimensions')).toBeInTheDocument()
  })

  it('collapses and expands', () => {
    const estimate = {
      total: {
        volumeMm3: 100,
        boundingBox: { width: 10, depth: 10, height: 10 },
      },
    }
    render(<ModelInfoPanel printEstimate={estimate} partCount={1} />)
    // Initially open
    expect(screen.getByText('info.volume')).toBeInTheDocument()
    // Collapse
    fireEvent.click(screen.getByText('info.title'))
    expect(screen.queryByText('info.volume')).not.toBeInTheDocument()
    // Expand again
    fireEvent.click(screen.getByText('info.title'))
    expect(screen.getByText('info.volume')).toBeInTheDocument()
  })

  it('sets aria-expanded on the toggle button', () => {
    const estimate = {
      total: {
        volumeMm3: 100,
        boundingBox: { width: 10, depth: 10, height: 10 },
      },
    }
    render(<ModelInfoPanel printEstimate={estimate} partCount={1} />)
    const button = screen.getByRole('button', { expanded: true })
    expect(button).toBeInTheDocument()
    fireEvent.click(button)
    expect(screen.getByRole('button', { expanded: false })).toBeInTheDocument()
  })
})
