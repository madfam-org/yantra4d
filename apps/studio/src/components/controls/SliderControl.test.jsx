import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SliderControl from './SliderControl'

const baseParam = {
  id: 'width',
  label: { en: 'Width', es: 'Ancho' },
  tooltip: { en: 'Width tooltip' },
  description: { en: 'Width desc' },
  min: 1,
  max: 10,
  step: 1,
  default: 5,
}

const defaultProps = {
  param: baseParam,
  value: 5,
  onSliderChange: vi.fn(),
  getLabel: (p, field, lang) => {
    if (typeof p[field] === 'object') return p[field][lang] || p[field].en
    return p[field] || ''
  },
  language: 'en',
  t: (key) => {
    const map = { 'ctrl.click_to_edit': 'Click to edit' }
    return map[key] || key
  },
}

function renderSlider(overrides = {}) {
  const props = { ...defaultProps, ...overrides }
  return render(<SliderControl {...props} />)
}

describe('SliderControl', () => {
  it('renders label and value display', () => {
    renderSlider()
    expect(screen.getByText('Width')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('renders default star indicator', () => {
    renderSlider()
    expect(screen.getByTestId('default-star-width')).toBeInTheDocument()
  })

  it('renders description when param has description', () => {
    renderSlider()
    expect(screen.getByText('Width desc')).toBeInTheDocument()
  })

  it('does not render description when param lacks it', () => {
    renderSlider({ param: { ...baseParam, description: undefined } })
    expect(screen.queryByText('Width desc')).not.toBeInTheDocument()
  })

  it('value display has correct aria attributes', () => {
    renderSlider()
    const valueBtn = screen.getByRole('button', { name: /Width: 5/ })
    expect(valueBtn).toHaveAttribute('tabIndex', '0')
  })

  it('clicking value enters edit mode with input', () => {
    renderSlider()
    fireEvent.click(screen.getByText('5'))
    const input = screen.getByRole('spinbutton')
    expect(input).toBeInTheDocument()
    expect(input).toHaveValue(5)
  })

  it('Enter key in edit mode commits clamped value', () => {
    const onSliderChange = vi.fn()
    renderSlider({ onSliderChange })
    // Enter edit mode
    fireEvent.click(screen.getByText('5'))
    const input = screen.getByRole('spinbutton')
    // Type value exceeding max
    fireEvent.change(input, { target: { value: '15' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    // Should clamp to max=10
    expect(onSliderChange).toHaveBeenCalledWith('width', [10])
  })

  it('Escape key cancels edit without calling onChange', () => {
    const onSliderChange = vi.fn()
    renderSlider({ onSliderChange })
    fireEvent.click(screen.getByText('5'))
    const input = screen.getByRole('spinbutton')
    fireEvent.change(input, { target: { value: '8' } })
    fireEvent.keyDown(input, { key: 'Escape' })
    expect(onSliderChange).not.toHaveBeenCalled()
    // Should exit edit mode - value display returns
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('blur commits the edit value', () => {
    const onSliderChange = vi.fn()
    renderSlider({ onSliderChange })
    fireEvent.click(screen.getByText('5'))
    const input = screen.getByRole('spinbutton')
    fireEvent.change(input, { target: { value: '3' } })
    fireEvent.blur(input)
    expect(onSliderChange).toHaveBeenCalledWith('width', [3])
  })

  it('clamps value below min', () => {
    const onSliderChange = vi.fn()
    renderSlider({ onSliderChange })
    fireEvent.click(screen.getByText('5'))
    const input = screen.getByRole('spinbutton')
    fireEvent.change(input, { target: { value: '0' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(onSliderChange).toHaveBeenCalledWith('width', [1])
  })

  it('snaps to step for fractional params', () => {
    const onSliderChange = vi.fn()
    const fractionalParam = { ...baseParam, min: 0, max: 10, step: 0.5, default: 2 }
    renderSlider({ param: fractionalParam, value: 2, onSliderChange })
    fireEvent.click(screen.getByText('2'))
    const input = screen.getByRole('spinbutton')
    fireEvent.change(input, { target: { value: '3.3' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    // 3.3 rounded to nearest 0.5 = 3.5
    expect(onSliderChange).toHaveBeenCalledWith('width', [3.5])
  })

  it('NaN input does not call onChange', () => {
    const onSliderChange = vi.fn()
    renderSlider({ onSliderChange })
    fireEvent.click(screen.getByText('5'))
    const input = screen.getByRole('spinbutton')
    fireEvent.change(input, { target: { value: 'abc' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(onSliderChange).not.toHaveBeenCalled()
  })

  it('disabled param has opacity-50 class', () => {
    const { container } = renderSlider({ param: { ...baseParam, disabled: true } })
    expect(container.firstChild).toHaveClass('opacity-50')
    expect(container.firstChild).toHaveClass('pointer-events-none')
  })

  it('does not render tick marks when step count exceeds 30', () => {
    const manySteps = { ...baseParam, min: 0, max: 100, step: 1 }
    const { container } = renderSlider({ param: manySteps, value: 50 })
    // 101 steps > 30 threshold, so no tick marks (only the star)
    const tickArea = container.querySelector('[aria-hidden="true"]')
    // Only the star should be present, no tick divs
    const ticks = tickArea.querySelectorAll('.w-px')
    expect(ticks.length).toBe(0)
  })

  it('renders tick marks when step count is within 30', () => {
    const fewSteps = { ...baseParam, min: 1, max: 5, step: 1 }
    const { container } = renderSlider({ param: fewSteps, value: 3 })
    const tickArea = container.querySelector('[aria-hidden="true"]')
    const ticks = tickArea.querySelectorAll('.w-px')
    // 5 steps total (1,2,3,4,5), minus the default tick (5) = 4 tick marks
    expect(ticks.length).toBeGreaterThan(0)
  })

  it('keyboard Enter/Space on value display enters edit mode', () => {
    renderSlider()
    const valueBtn = screen.getByRole('button', { name: /Width: 5/ })
    fireEvent.keyDown(valueBtn, { key: 'Enter' })
    expect(screen.getByRole('spinbutton')).toBeInTheDocument()
  })

  it('uses star override when param.star is set', () => {
    const paramWithStar = { ...baseParam, star: 3 }
    renderSlider({ param: paramWithStar })
    // Star should still render
    expect(screen.getByTestId('default-star-width')).toBeInTheDocument()
  })

  it('falls back to param.default when value is undefined', () => {
    renderSlider({ value: undefined })
    // Should display param.default (5) instead of crashing or showing 100
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('falls back to param.default when value is null', () => {
    renderSlider({ value: null })
    expect(screen.getByText('5')).toBeInTheDocument()
  })
})
