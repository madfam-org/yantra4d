import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ColorGradientControl from './ColorGradientControl'

const baseParam = {
  id: 'gradient_color',
  label: { en: 'Color Gradient', es: 'Gradiente de Color' },
  tooltip: { en: 'Gradient tooltip' },
}

const defaultProps = {
  param: baseParam,
  value: { start: '#ff0000', end: '#0000ff' },
  onChange: vi.fn(),
  getLabel: (p, field, lang) => {
    if (typeof p[field] === 'object') return p[field][lang] || p[field].en
    return p[field] || ''
  },
  language: 'en',
}

function renderGradient(overrides = {}) {
  return render(<ColorGradientControl {...defaultProps} {...overrides} />)
}

describe('ColorGradientControl', () => {
  it('renders label', () => {
    renderGradient()
    expect(screen.getByText('Color Gradient')).toBeInTheDocument()
  })

  it('renders start and end color inputs', () => {
    renderGradient()
    const startInput = document.getElementById('gradient-start-gradient_color')
    const endInput = document.getElementById('gradient-end-gradient_color')
    expect(startInput).toBeInTheDocument()
    expect(endInput).toBeInTheDocument()
    expect(startInput).toHaveAttribute('type', 'color')
    expect(endInput).toHaveAttribute('type', 'color')
  })

  it('displays current color values in inputs', () => {
    renderGradient()
    expect(screen.getByDisplayValue('#ff0000')).toBeInTheDocument()
    expect(screen.getByDisplayValue('#0000ff')).toBeInTheDocument()
  })

  it('uses default colors when value is null', () => {
    renderGradient({ value: null })
    expect(screen.getByDisplayValue('#ff0000')).toBeInTheDocument()
    expect(screen.getByDisplayValue('#0000ff')).toBeInTheDocument()
  })

  it('renders gradient preview with aria-label', () => {
    renderGradient()
    const preview = screen.getByLabelText('Gradient preview: #ff0000 to #0000ff')
    expect(preview).toBeInTheDocument()
  })

  it('changing start color calls onChange with updated value', () => {
    const onChange = vi.fn()
    renderGradient({ onChange })
    const startInput = document.getElementById('gradient-start-gradient_color')
    fireEvent.change(startInput, { target: { value: '#00ff00' } })
    expect(onChange).toHaveBeenCalledWith('gradient_color', { start: '#00ff00', end: '#0000ff' })
  })

  it('changing end color calls onChange with updated value', () => {
    const onChange = vi.fn()
    renderGradient({ onChange })
    const endInput = document.getElementById('gradient-end-gradient_color')
    fireEvent.change(endInput, { target: { value: '#ffff00' } })
    expect(onChange).toHaveBeenCalledWith('gradient_color', { start: '#ff0000', end: '#ffff00' })
  })

  it('shows Spanish labels when language is es', () => {
    renderGradient({ language: 'es' })
    expect(screen.getByText('Inicio')).toBeInTheDocument()
    expect(screen.getByText('Fin')).toBeInTheDocument()
  })

  it('shows English labels when language is en', () => {
    renderGradient({ language: 'en' })
    expect(screen.getByText('Start')).toBeInTheDocument()
    expect(screen.getByText('End')).toBeInTheDocument()
  })
})
