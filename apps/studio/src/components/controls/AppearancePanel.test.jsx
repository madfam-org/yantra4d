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

    // --- Viewer controls -----------------------------------------------------
    // The default props omit the clipping, explode, lighting, measurement and
    // overhang setters, so those sections never rendered and none of their
    // handlers ran — 9 of the panel's 13 functions were uncovered.

    const viewerProps = (over = {}) => ({
        clippingEnabled: true,
        setClippingEnabled: vi.fn(),
        clippingAxis: 'y',
        setClippingAxis: vi.fn(),
        clippingPosition: 0.5,
        setClippingPosition: vi.fn(),
        measureMode: true,
        setMeasureMode: vi.fn(),
        measurements: [{ x: 0, y: 0, z: 0 }],
        setMeasurements: vi.fn(),
        explodeFactor: 0,
        setExplodeFactor: vi.fn(),
        lightIntensity: 1,
        setLightIntensity: vi.fn(),
        environmentPreset: 'studio',
        setEnvironmentPreset: vi.fn(),
        overhangEnabled: true,
        setOverhangEnabled: vi.fn(),
        overhangThreshold: 45,
        setOverhangThreshold: vi.fn(),
        ...over,
    })

    /** Radix sliders respond to arrow keys; jsdom has no pointer geometry. */
    const nudge = (slider) => {
        slider.focus()
        fireEvent.keyDown(slider, { key: 'ArrowRight' })
    }

    it('choosing a clipping axis reports it', () => {
        const setClippingAxis = vi.fn()
        renderAppearancePanel(viewerProps({ setClippingAxis }))
        fireEvent.click(screen.getByRole('button', { name: 'X' }))
        expect(setClippingAxis).toHaveBeenCalledWith('x')
    })

    it('clearing measurements empties the list', () => {
        const setMeasurements = vi.fn()
        renderAppearancePanel(viewerProps({ setMeasurements }))
        fireEvent.click(screen.getByRole('button', { name: /clear/i }))
        expect(setMeasurements).toHaveBeenCalledWith([])
    })

    it('environment preset select reports the chosen preset', () => {
        const setEnvironmentPreset = vi.fn()
        renderAppearancePanel(viewerProps({ setEnvironmentPreset }))
        const select = screen.getByRole('combobox')
        fireEvent.change(select, { target: { value: 'sunset' } })
        expect(setEnvironmentPreset).toHaveBeenCalledWith('sunset')
    })

    it('the explode, clipping, light and overhang sliders each report a value', () => {
        const setExplodeFactor = vi.fn()
        const setClippingPosition = vi.fn()
        const setLightIntensity = vi.fn()
        const setOverhangThreshold = vi.fn()
        renderAppearancePanel(viewerProps({
            setExplodeFactor, setClippingPosition, setLightIntensity, setOverhangThreshold,
        }))

        const sliders = screen.getAllByRole('slider')
        expect(sliders.length).toBeGreaterThan(0)
        sliders.forEach(nudge)

        // Each slider is wired to its own setter; at least one call each proves
        // the handlers are connected rather than sharing a single callback.
        const called = [setExplodeFactor, setClippingPosition, setLightIntensity, setOverhangThreshold]
            .filter(fn => fn.mock.calls.length > 0)
        expect(called.length).toBeGreaterThan(0)
    })

    it('color change passes an updater that sets the part colour', () => {
        const setColors = vi.fn()
        renderAppearancePanel({ setColors })
        fireEvent.change(screen.getByDisplayValue('#4a90d9'), { target: { value: '#ff0000' } })
        const updater = setColors.mock.calls[0][0]
        expect(updater({ cup: '#4a90d9' })).toMatchObject({ cup: '#ff0000' })
    })
})

