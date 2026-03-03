import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'

vi.mock('three', () => {
  class Color {
    constructor(c) {
      this.r = 0; this.g = 0; this.b = 0
      if (c === '#ef4444') { this.r = 1 }
      else if (c === '#22c55e') { this.g = 1 }
      else if (c === '#eab308') { this.r = 0.9; this.g = 0.7 }
    }
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

import OverhangOverlay from './OverhangOverlay'

describe('OverhangOverlay', () => {
  it('exports a function component', () => {
    expect(typeof OverhangOverlay).toBe('function')
  })

  it('returns null when no points provided', () => {
    const { container } = render(<OverhangOverlay points={[]} angles={[]} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders points when data is provided', () => {
    const points = [[0, 0, 0], [1, 1, 1], [2, 2, 2]]
    const angles = [10, 30, 60]
    // Should not throw when rendering with valid data
    render(<OverhangOverlay points={points} angles={angles} threshold={45} />)
  })

  it('handles default props', () => {
    // Rendering with no props should not throw
    render(<OverhangOverlay />)
  })
})
