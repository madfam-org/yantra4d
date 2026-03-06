import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import AppearancePanel from './AppearancePanel'
import { renderWithProviders } from '../../test/render-with-providers'

function renderAppearancePanel(props = {}) {
    const defaultProps = {
        mode: 'cup',
        colors: { cup: '#4a90d9' },
        setColors: vi.fn(),
        wireframe: false,
        setWireframe: vi.fn(),
        boundingBox: false,
        setBoundingBox: vi.fn(),
    }

    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('no backend'))

    return renderWithProviders(<AppearancePanel {...defaultProps} {...props} />)
}

describe('AppearancePanel', () => {
    it('renders color picker for cup mode (cup part)', () => {
        renderAppearancePanel()
        const colorInput = screen.getByDisplayValue('#4a90d9')
        expect(colorInput).toBeInTheDocument()
        expect(colorInput).toHaveAttribute('type', 'color')
    })

    it('color change calls setColors', () => {
        const setColors = vi.fn()
        renderAppearancePanel({ setColors })
        const colorInput = screen.getByDisplayValue('#4a90d9')
        fireEvent.change(colorInput, { target: { value: '#ff0000' } })
        expect(setColors).toHaveBeenCalled()
    })

    it('renders colors group label for part color controls', () => {
        renderAppearancePanel()
        expect(screen.getByText('Colors')).toBeInTheDocument()
    })

    it('renders wireframe toggle when setWireframe is provided', () => {
        const setWireframe = vi.fn()
        renderAppearancePanel({ wireframe: false, setWireframe })
        expect(screen.getByText('Wireframe')).toBeInTheDocument()
    })

    it('renders bounding box toggle when setBoundingBox is provided', () => {
        const setBoundingBox = vi.fn()
        renderAppearancePanel({ boundingBox: false, setBoundingBox })
        expect(screen.getByText('Bounding Box')).toBeInTheDocument()
    })
})
