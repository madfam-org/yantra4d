import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'

// Mock R3F dependencies before import
vi.mock('@react-three/drei', () => ({
  Text: ({ children, ...props }) => <span data-testid="drei-text" {...props}>{children}</span>,
  Line: ({ color }) => <div data-testid="drei-line" data-color={color} />,
}))

import NumberedAxes from './NumberedAxes'

describe('NumberedAxes', () => {
  it('renders three axis groups (X, Y, Z)', () => {
    const { container } = render(<NumberedAxes />)
    // Each axis has a label text: X, Y, Z
    const texts = container.querySelectorAll('[data-testid="drei-text"]')
    const labels = Array.from(texts).map(t => t.textContent)
    expect(labels).toContain('X')
    expect(labels).toContain('Y')
    expect(labels).toContain('Z')
  })

  it('renders tick marks at interval of 10 up to 100', () => {
    const { container } = render(<NumberedAxes />)
    const texts = container.querySelectorAll('[data-testid="drei-text"]')
    const values = Array.from(texts).map(t => t.textContent)
    // Each axis should have ticks: 10, 20, ..., 100 (10 ticks per axis)
    // Plus the label text (X, Y, Z) = 33 total
    expect(values).toContain('10')
    expect(values).toContain('50')
    expect(values).toContain('100')
  })

  it('renders lines for axes and tick marks', () => {
    const { container } = render(<NumberedAxes />)
    const lines = container.querySelectorAll('[data-testid="drei-line"]')
    // 3 axis lines + 10 ticks per axis * 3 axes = 33 lines
    expect(lines.length).toBe(33)
  })

  it('uses default axis colors (red, green, blue)', () => {
    const { container } = render(<NumberedAxes />)
    const lines = container.querySelectorAll('[data-testid="drei-line"]')
    const colors = Array.from(lines).map(l => l.getAttribute('data-color'))
    expect(colors).toContain('#ef4444') // red for X
    expect(colors).toContain('#22c55e') // green for Y
    expect(colors).toContain('#3b82f6') // blue for Z
  })

  it('accepts custom axis colors', () => {
    const customColors = ['#000000', '#111111', '#222222']
    const { container } = render(<NumberedAxes axisColors={customColors} />)
    const lines = container.querySelectorAll('[data-testid="drei-line"]')
    const colors = Array.from(lines).map(l => l.getAttribute('data-color'))
    expect(colors).toContain('#000000')
    expect(colors).toContain('#111111')
    expect(colors).toContain('#222222')
    expect(colors).not.toContain('#ef4444')
  })
})
