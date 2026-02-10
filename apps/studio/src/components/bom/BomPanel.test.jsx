import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import BomPanel from './BomPanel'

// Mock useLanguage
vi.mock('../../contexts/LanguageProvider', () => ({
  useLanguage: () => ({
    language: 'en',
    t: (key) => {
      const translations = {
        'bom.title': 'Bill of Materials',
        'bom.item': 'Item',
        'bom.qty': 'Qty',
        'bom.unit': 'Unit',
      }
      return translations[key] || key
    },
  }),
}))

// Mock useManifest
const mockManifest = {
  bom: {
    hardware: [
      {
        id: 'magnets_6x2',
        label: { es: 'Imanes N52 6×2mm', en: 'N52 6×2mm Magnets' },
        quantity_formula: '(enable_magnets ? 4 : 0) + (bp_enable_magnets ? 4 * width_units * depth_units : 0)',
        unit: 'pcs',
      },
      {
        id: 'screws_m3x6',
        label: { es: 'Tornillos M3×6', en: 'M3×6 Screws' },
        quantity_formula: '(enable_screws ? 4 : 0) + (bp_enable_screws ? 4 : 0)',
        unit: 'pcs',
      },
    ],
  },
}

vi.mock('../../contexts/ManifestProvider', () => ({
  useManifest: () => ({
    manifest: mockManifest,
    getLabel: (obj, key, lang) => {
      const val = obj[key]
      if (typeof val === 'string') return val
      return val?.[lang] || val?.en || ''
    },
  }),
}))

describe('BomPanel', () => {
  it('renders BOM table with hardware items', () => {
    const params = { enable_magnets: true, enable_screws: false, bp_enable_magnets: false, bp_enable_screws: false, width_units: 2, depth_units: 1 }
    render(<BomPanel params={params} />)

    expect(screen.getByText('Bill of Materials')).toBeInTheDocument()
    expect(screen.getByText('N52 6×2mm Magnets')).toBeInTheDocument()
    expect(screen.getByText('M3×6 Screws')).toBeInTheDocument()
  })

  it('evaluates quantity_formula with current params', () => {
    const params = { enable_magnets: true, enable_screws: false, bp_enable_magnets: false, bp_enable_screws: false, width_units: 2, depth_units: 1 }
    render(<BomPanel params={params} />)

    // enable_magnets=true → 4, bp_enable_magnets=false → 0, total = 4
    expect(screen.getByText('4')).toBeInTheDocument()
    // enable_screws=false → 0, bp_enable_screws=false → 0, total = 0
    expect(screen.getByText('0')).toBeInTheDocument()
  })

  it('computes baseplate magnet quantities correctly', () => {
    const params = { enable_magnets: false, enable_screws: false, bp_enable_magnets: true, bp_enable_screws: false, width_units: 3, depth_units: 2 }
    render(<BomPanel params={params} />)

    // bp_enable_magnets=true → 4 * 3 * 2 = 24
    expect(screen.getByText('24')).toBeInTheDocument()
  })

  it('renders unit column', () => {
    const params = { enable_magnets: true, enable_screws: false, bp_enable_magnets: false, bp_enable_screws: false, width_units: 2, depth_units: 1 }
    render(<BomPanel params={params} />)

    const pcsCells = screen.getAllByText('pcs')
    expect(pcsCells.length).toBeGreaterThanOrEqual(2)
  })

  it('renders nothing when no BOM in manifest', () => {
    // Override manifest mock for this test
    const originalManifest = mockManifest.bom
    mockManifest.bom = undefined

    const { container } = render(<BomPanel params={{}} />)
    expect(container.firstChild).toBeNull()

    mockManifest.bom = originalManifest
  })

  it('renders nothing when hardware array is empty', () => {
    const originalHardware = mockManifest.bom.hardware
    mockManifest.bom.hardware = []

    const { container } = render(<BomPanel params={{}} />)
    expect(container.firstChild).toBeNull()

    mockManifest.bom.hardware = originalHardware
  })

  it('handles numeric quantity_formula', () => {
    const originalHardware = mockManifest.bom.hardware
    mockManifest.bom.hardware = [
      { id: 'felt', label: { en: 'Felt liner' }, quantity_formula: 1, unit: 'sheet' },
    ]

    render(<BomPanel params={{}} />)
    expect(screen.getByText('Felt liner')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('sheet')).toBeInTheDocument()

    mockManifest.bom.hardware = originalHardware
  })

  it('renders table headers', () => {
    const params = { enable_magnets: true, enable_screws: false, bp_enable_magnets: false, bp_enable_screws: false, width_units: 2, depth_units: 1 }
    render(<BomPanel params={params} />)

    expect(screen.getByText('Item')).toBeInTheDocument()
    expect(screen.getByText('Qty')).toBeInTheDocument()
    expect(screen.getByText('Unit')).toBeInTheDocument()
  })
})
