import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'

vi.mock('@react-three/fiber', () => ({
  useThree: () => ({}),
}))

vi.mock('three', () => {
  class Color {
    constructor(c) { this.r = 0; this.g = 0; this.b = 0; if (c === '#ef4444') { this.r = 1 } else if (c === '#22c55e') { this.g = 1 } else if (c === '#eab308') { this.r = 0.9; this.g = 0.7 } }
    lerpColors() { return this }
  }
  return {
    Color,
    BufferAttribute: class {},
    Points: class {},
    PointsMaterial: class {},
    BufferGeometry: class {},
  }
})

import ThicknessOverlay from './ThicknessOverlay'

describe('ThicknessOverlay', () => {
  it('returns null when no points provided', () => {
    const { container } = render(<ThicknessOverlay points={[]} thicknesses={[]} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders points when data is provided', () => {
    const points = [[0, 0, 0], [1, 1, 1], [2, 2, 2]]
    const thicknesses = [0.5, 1.0, 1.5]
    // Should not throw
    render(<ThicknessOverlay points={points} thicknesses={thicknesses} />)
  })

  it('handles Infinity thickness values', () => {
    const points = [[0, 0, 0]]
    const thicknesses = [Infinity]
    render(<ThicknessOverlay points={points} thicknesses={thicknesses} />)
  })
})
