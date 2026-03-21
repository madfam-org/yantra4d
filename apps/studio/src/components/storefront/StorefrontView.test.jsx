import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// Use vi.hoisted so the mutable ref is available to the hoisted vi.mock calls
const { mockManifestData } = vi.hoisted(() => {
  return {
    mockManifestData: {
      current: {
        manifest: {
          project: {
            name: 'Test Product',
            slug: 'test-product',
            description: 'A test product',
            tags: ['hyperobject', 'demo'],
          },
          presets: [
            { id: 'small', label: 'Small', values: { width: 10 } },
            { id: 'large', label: 'Large', values: { width: 50 }, emoji: '\u{1F3E0}' },
          ],
          bom: [
            { id: 'bolt', label: 'M3 Bolt', qty: 4, supplier: 'McMaster', url: 'https://example.com' },
            { id: 'nut', label: 'M3 Nut', qty: 4, supplier: 'Local' },
          ],
          modes: [{ id: 'default' }],
        },
        getLabel: (val) => (typeof val === 'object' ? val?.en : val) || val,
      },
    },
  }
})

vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({ language: 'en', t: (key, fallback) => fallback || key }),
}))

vi.mock('../../contexts/project/ManifestProvider', () => ({
  useManifest: () => mockManifestData.current,
}))

const mockSetParams = vi.fn()
const mockHandleGenerate = vi.fn()
vi.mock('../../contexts/project/ProjectProvider', () => ({
  useProject: () => ({
    setParams: mockSetParams,
    handleGenerate: mockHandleGenerate,
    projectSlug: 'test-product',
  }),
}))

import StorefrontView from './StorefrontView'

// Default manifest snapshot used by most tests
const DEFAULT_MANIFEST = {
  manifest: {
    project: {
      name: 'Test Product',
      slug: 'test-product',
      description: 'A test product',
      tags: ['hyperobject', 'demo'],
    },
    presets: [
      { id: 'small', label: 'Small', values: { width: 10 } },
      { id: 'large', label: 'Large', values: { width: 50 }, emoji: '\u{1F3E0}' },
    ],
    bom: [
      { id: 'bolt', label: 'M3 Bolt', qty: 4, supplier: 'McMaster', url: 'https://example.com' },
      { id: 'nut', label: 'M3 Nut', qty: 4, supplier: 'Local' },
    ],
    modes: [{ id: 'default' }],
  },
  getLabel: (val) => (typeof val === 'object' ? val?.en : val) || val,
}

describe('StorefrontView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset to default manifest before each test
    mockManifestData.current = { ...DEFAULT_MANIFEST }
  })

  it('renders product name and description', () => {
    render(<StorefrontView />)
    expect(screen.getByTestId('storefront-title')).toHaveTextContent('Test Product')
    expect(screen.getByText('A test product')).toBeInTheDocument()
  })

  it('renders product tags', () => {
    render(<StorefrontView />)
    expect(screen.getByText('#hyperobject')).toBeInTheDocument()
    expect(screen.getByText('#demo')).toBeInTheDocument()
  })

  it('renders preset gallery', () => {
    render(<StorefrontView />)
    expect(screen.getByTestId('preset-gallery')).toBeInTheDocument()
    expect(screen.getByTestId('preset-card-small')).toBeInTheDocument()
    expect(screen.getByTestId('preset-card-large')).toBeInTheDocument()
  })

  it('renders BOM table', () => {
    render(<StorefrontView />)
    expect(screen.getByTestId('storefront-bom')).toBeInTheDocument()
    expect(screen.getByText('M3 Bolt')).toBeInTheDocument()
    expect(screen.getAllByText('4')).toHaveLength(2) // qty 4 for both bolt and nut
    expect(screen.getByText('McMaster')).toBeInTheDocument()
  })

  it('BOM link renders for items with URL', () => {
    render(<StorefrontView />)
    const link = screen.getByText('McMaster')
    expect(link.tagName).toBe('A')
    expect(link).toHaveAttribute('href', 'https://example.com')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('BOM item without URL renders supplier as plain text', () => {
    render(<StorefrontView />)
    // M3 Nut has supplier but no URL
    const nutRow = screen.getByText('M3 Nut').closest('tr')
    const cells = nutRow.querySelectorAll('td')
    expect(cells[2].textContent).toBe('Local')
    expect(cells[2].querySelector('a')).toBeNull()
  })

  it('renders Download STL button', () => {
    render(<StorefrontView />)
    expect(screen.getByTestId('storefront-generate')).toBeInTheDocument()
    expect(screen.getByText('Download STL')).toBeInTheDocument()
  })

  it('clicking Download STL calls handleGenerate', () => {
    render(<StorefrontView />)
    fireEvent.click(screen.getByTestId('storefront-generate'))
    expect(mockHandleGenerate).toHaveBeenCalledOnce()
  })

  it('share button appears after selecting a preset', () => {
    render(<StorefrontView />)
    // Initially no share button
    expect(screen.queryByTestId('storefront-share')).not.toBeInTheDocument()
    // Select a preset
    fireEvent.click(screen.getByTestId('preset-card-small'))
    expect(screen.getByTestId('storefront-share')).toBeInTheDocument()
  })

  it('selecting a preset calls setParams with preset values', () => {
    render(<StorefrontView />)
    fireEvent.click(screen.getByTestId('preset-card-small'))
    expect(mockSetParams).toHaveBeenCalled()
  })

  it('renders exit button when onExitStorefront is provided', () => {
    const onExit = vi.fn()
    render(<StorefrontView onExitStorefront={onExit} />)
    const exitBtn = screen.getByTestId('exit-storefront')
    expect(exitBtn).toBeInTheDocument()
    fireEvent.click(exitBtn)
    expect(onExit).toHaveBeenCalledOnce()
  })

  it('does not render exit button when no callback provided', () => {
    render(<StorefrontView />)
    expect(screen.queryByTestId('exit-storefront')).not.toBeInTheDocument()
  })

  it('preset card shows emoji when present', () => {
    render(<StorefrontView />)
    // The "Large" preset has emoji
    const largeCard = screen.getByTestId('preset-card-large')
    expect(largeCard.textContent).toContain('\u{1F3E0}')
  })

  it('preset card shows values summary', () => {
    render(<StorefrontView />)
    expect(screen.getAllByText('width').length).toBeGreaterThan(0)
  })

  it('active preset shows Active badge', () => {
    render(<StorefrontView />)
    fireEvent.click(screen.getByTestId('preset-card-small'))
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  // --- New tests for uncovered branches ---

  describe('no description', () => {
    it('does not render description paragraph when description is empty', () => {
      mockManifestData.current = {
        ...DEFAULT_MANIFEST,
        manifest: {
          ...DEFAULT_MANIFEST.manifest,
          project: {
            name: 'No Desc Product',
            slug: 'no-desc',
            description: '',
            tags: ['test'],
          },
        },
      }
      render(<StorefrontView />)
      expect(screen.getByTestId('storefront-title')).toHaveTextContent('No Desc Product')
      // No description <p> should exist next to the title
      const titleParent = screen.getByTestId('storefront-title').parentElement
      expect(titleParent.querySelector('p')).toBeNull()
    })

    it('does not render description paragraph when description is null/undefined', () => {
      mockManifestData.current = {
        ...DEFAULT_MANIFEST,
        manifest: {
          ...DEFAULT_MANIFEST.manifest,
          project: {
            name: 'Null Desc Product',
            slug: 'null-desc',
            tags: [],
          },
        },
      }
      render(<StorefrontView />)
      expect(screen.getByTestId('storefront-title')).toHaveTextContent('Null Desc Product')
      const titleParent = screen.getByTestId('storefront-title').parentElement
      expect(titleParent.querySelector('p')).toBeNull()
    })
  })

  describe('no tags', () => {
    it('does not render tags section when tags array is empty', () => {
      mockManifestData.current = {
        ...DEFAULT_MANIFEST,
        manifest: {
          ...DEFAULT_MANIFEST.manifest,
          project: {
            name: 'No Tags Product',
            slug: 'no-tags',
            description: 'Has description but no tags',
            tags: [],
          },
        },
      }
      render(<StorefrontView />)
      expect(screen.getByText('Has description but no tags')).toBeInTheDocument()
      // No tag spans (prefixed with #) should exist
      expect(screen.queryByText(/^#/)).not.toBeInTheDocument()
    })

    it('does not render tags section when tags is undefined', () => {
      mockManifestData.current = {
        ...DEFAULT_MANIFEST,
        manifest: {
          ...DEFAULT_MANIFEST.manifest,
          project: {
            name: 'Undef Tags Product',
            slug: 'undef-tags',
            description: 'A product',
          },
        },
      }
      render(<StorefrontView />)
      expect(screen.queryByText(/^#/)).not.toBeInTheDocument()
    })
  })

  describe('no presets', () => {
    it('does not render preset gallery section when presets is empty', () => {
      mockManifestData.current = {
        ...DEFAULT_MANIFEST,
        manifest: {
          ...DEFAULT_MANIFEST.manifest,
          presets: [],
        },
      }
      render(<StorefrontView />)
      expect(screen.queryByTestId('preset-gallery')).not.toBeInTheDocument()
    })

    it('share button never appears when there are no presets to select', () => {
      mockManifestData.current = {
        ...DEFAULT_MANIFEST,
        manifest: {
          ...DEFAULT_MANIFEST.manifest,
          presets: [],
        },
      }
      render(<StorefrontView />)
      // No preset to click, so share button cannot appear
      expect(screen.queryByTestId('storefront-share')).not.toBeInTheDocument()
    })
  })

  describe('no BOM', () => {
    it('does not render BOM section when bom array is empty', () => {
      mockManifestData.current = {
        ...DEFAULT_MANIFEST,
        manifest: {
          ...DEFAULT_MANIFEST.manifest,
          bom: [],
        },
      }
      render(<StorefrontView />)
      expect(screen.queryByTestId('storefront-bom')).not.toBeInTheDocument()
    })

    it('does not render BOM section when bom is undefined', () => {
      mockManifestData.current = {
        ...DEFAULT_MANIFEST,
        manifest: {
          project: DEFAULT_MANIFEST.manifest.project,
          presets: DEFAULT_MANIFEST.manifest.presets,
          modes: DEFAULT_MANIFEST.manifest.modes,
          // bom intentionally omitted
        },
      }
      render(<StorefrontView />)
      expect(screen.queryByTestId('storefront-bom')).not.toBeInTheDocument()
    })
  })

  describe('BOM edge cases', () => {
    it('renders dash when BOM item has no supplier and no URL', () => {
      mockManifestData.current = {
        ...DEFAULT_MANIFEST,
        manifest: {
          ...DEFAULT_MANIFEST.manifest,
          bom: [
            { id: 'washer', label: 'M3 Washer', qty: 8 },
          ],
        },
      }
      render(<StorefrontView />)
      const washerRow = screen.getByText('M3 Washer').closest('tr')
      const cells = washerRow.querySelectorAll('td')
      // supplier column should show dash
      expect(cells[2].textContent).toBe('\u2014')
      expect(cells[2].querySelector('a')).toBeNull()
    })

    it('renders "Buy" fallback when BOM item has URL but no supplier', () => {
      mockManifestData.current = {
        ...DEFAULT_MANIFEST,
        manifest: {
          ...DEFAULT_MANIFEST.manifest,
          bom: [
            { id: 'screw', label: 'M3 Screw', qty: 2, url: 'https://buy.example.com' },
          ],
        },
      }
      render(<StorefrontView />)
      const screwRow = screen.getByText('M3 Screw').closest('tr')
      const cells = screwRow.querySelectorAll('td')
      const link = cells[2].querySelector('a')
      expect(link).not.toBeNull()
      expect(link.textContent).toBe('Buy')
      expect(link).toHaveAttribute('href', 'https://buy.example.com')
      expect(link).toHaveAttribute('target', '_blank')
    })

    it('renders item.id as fallback when label is missing', () => {
      mockManifestData.current = {
        ...DEFAULT_MANIFEST,
        manifest: {
          ...DEFAULT_MANIFEST.manifest,
          bom: [
            { id: 'spring_pin', qty: 1, supplier: 'Amazon' },
          ],
        },
      }
      render(<StorefrontView />)
      expect(screen.getByText('spring_pin')).toBeInTheDocument()
    })

    it('defaults qty to 1 when qty is not specified', () => {
      mockManifestData.current = {
        ...DEFAULT_MANIFEST,
        manifest: {
          ...DEFAULT_MANIFEST.manifest,
          bom: [
            { id: 'widget', label: 'Widget' },
          ],
        },
      }
      render(<StorefrontView />)
      const row = screen.getByText('Widget').closest('tr')
      const cells = row.querySelectorAll('td')
      expect(cells[1].textContent).toBe('1')
    })
  })

  describe('share button flow', () => {
    it('clicking share copies URL from API and shows copied state', async () => {
      const mockClipboard = { writeText: vi.fn().mockResolvedValue(undefined) }
      Object.assign(navigator, { clipboard: mockClipboard })

      globalThis.fetch = vi.fn().mockResolvedValue({
        json: () => Promise.resolve({ share_url: 'https://app.yantra4d.com/share/abc123' }),
      })

      render(<StorefrontView />)

      // Select a preset first to make share button appear
      fireEvent.click(screen.getByTestId('preset-card-small'))
      expect(screen.getByTestId('storefront-share')).toBeInTheDocument()

      // Click share
      fireEvent.click(screen.getByTestId('storefront-share'))

      await waitFor(() => {
        expect(screen.getByText('Link copied!')).toBeInTheDocument()
      })

      expect(mockClipboard.writeText).toHaveBeenCalledWith('https://app.yantra4d.com/share/abc123')
    })

    it('falls back to copying current URL when API fetch fails', async () => {
      const mockClipboard = { writeText: vi.fn().mockResolvedValue(undefined) }
      Object.assign(navigator, { clipboard: mockClipboard })

      globalThis.fetch = vi.fn().mockRejectedValue(new Error('API down'))

      render(<StorefrontView />)

      // Select a preset first
      fireEvent.click(screen.getByTestId('preset-card-small'))

      // Click share
      fireEvent.click(screen.getByTestId('storefront-share'))

      await waitFor(() => {
        expect(screen.getByText('Link copied!')).toBeInTheDocument()
      })

      // Falls back to window.location.href
      expect(mockClipboard.writeText).toHaveBeenCalledWith(window.location.href)
    })

    it('does not call fetch when no preset is active', () => {
      globalThis.fetch = vi.fn()
      render(<StorefrontView />)

      // Share button not visible when no preset active
      expect(screen.queryByTestId('storefront-share')).not.toBeInTheDocument()
      expect(globalThis.fetch).not.toHaveBeenCalled()
    })
  })

  describe('project name fallback', () => {
    it('falls back to slug when name is empty', () => {
      mockManifestData.current = {
        ...DEFAULT_MANIFEST,
        manifest: {
          ...DEFAULT_MANIFEST.manifest,
          project: {
            slug: 'fallback-slug',
            tags: [],
          },
        },
        getLabel: () => '',
      }
      render(<StorefrontView />)
      expect(screen.getByTestId('storefront-title')).toHaveTextContent('fallback-slug')
    })
  })
})
