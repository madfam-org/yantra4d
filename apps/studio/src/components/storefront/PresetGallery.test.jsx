import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock providers
vi.mock('../../contexts/system/LanguageProvider', () => ({
    useLanguage: () => ({
        t: (key, fallback) => fallback || key,
    }),
}))

vi.mock('../../contexts/project/ManifestProvider', () => ({
    useManifest: () => ({
        getLabel: (label) => (typeof label === 'object' ? label.en : label),
    }),
}))

import PresetGallery from './PresetGallery'

const MOCK_PRESETS = [
    {
        id: 'compact',
        label: { en: 'Compact' },
        emoji: '📦',
        values: { height: 10, width: 20, depth: 5 },
    },
    {
        id: 'large',
        label: { en: 'Large' },
        values: { height: 50, width: 100 },
        visible_in_modes: ['default'],
    },
    {
        id: 'hidden',
        label: { en: 'Hidden' },
        visible_in_modes: ['advanced'],
    },
]

describe('PresetGallery', () => {
    const defaultProps = {
        presets: MOCK_PRESETS,
        currentMode: 'default',
        onSelect: vi.fn(),
        activePreset: null,
    }

    it('renders null when no visible presets', () => {
        const { container } = render(
            <PresetGallery presets={[]} currentMode="default" onSelect={vi.fn()} />
        )
        expect(container.innerHTML).toBe('')
    })

    it('renders visible presets for current mode', () => {
        render(<PresetGallery {...defaultProps} />)
        expect(screen.getByText('Compact')).toBeInTheDocument()
        expect(screen.getByText('Large')).toBeInTheDocument()
        // 'Hidden' should not appear (only visible in 'advanced' mode)
        expect(screen.queryByText('Hidden')).not.toBeInTheDocument()
    })

    it('shows emoji badge when present', () => {
        render(<PresetGallery {...defaultProps} />)
        expect(screen.getByText('📦')).toBeInTheDocument()
    })

    it('shows parameter values summary', () => {
        render(<PresetGallery {...defaultProps} />)
        // "height" appears in multiple preset cards, use getAllByText
        const heightLabels = screen.getAllByText('height')
        expect(heightLabels.length).toBeGreaterThanOrEqual(1)
        expect(screen.getAllByText('10').length).toBeGreaterThanOrEqual(1)
    })

    it('calls onSelect when a preset card is clicked', () => {
        const onSelect = vi.fn()
        render(<PresetGallery {...defaultProps} onSelect={onSelect} />)
        fireEvent.click(screen.getByTestId('preset-card-compact'))
        expect(onSelect).toHaveBeenCalledWith(MOCK_PRESETS[0])
    })

    it('highlights the active preset', () => {
        render(<PresetGallery {...defaultProps} activePreset="compact" />)
        const card = screen.getByTestId('preset-card-compact')
        expect(card).toHaveAttribute('aria-pressed', 'true')
        expect(screen.getByText('Active')).toBeInTheDocument()
    })

    it('renders the heading', () => {
        render(<PresetGallery {...defaultProps} />)
        expect(screen.getByText('Configurations')).toBeInTheDocument()
    })
})
