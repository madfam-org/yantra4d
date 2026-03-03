import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'

const mockGl = { clippingPlanes: [] }
const mockUseThree = vi.fn(() => ({ gl: mockGl }))

vi.mock('@react-three/fiber', () => ({
  useThree: () => mockUseThree(),
}))

vi.mock('three', () => {
  class Vector3 {
    constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z }
    clone() { return new Vector3(this.x, this.y, this.z) }
    sub() { return this }
    multiplyScalar() { return this }
    toArray() { return [this.x, this.y, this.z] }
  }
  class Plane {
    constructor(normal, constant) { this.normal = normal; this.constant = constant }
  }
  return {
    Vector3,
    Plane,
    DoubleSide: 2,
  }
})

import ClippingPlane from './ClippingPlane'

describe('ClippingPlane', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGl.clippingPlanes = []
  })

  it('sets clipping planes on the renderer', () => {
    const bbox = {
      min: { x: 0, y: 0, z: 0 },
      max: { x: 100, y: 100, z: 100 },
      getSize: vi.fn(() => ({ x: 100, y: 100, z: 100 })),
    }
    render(<ClippingPlane axis="z" position={0.5} bbox={bbox} />)
    expect(mockGl.clippingPlanes).toHaveLength(1)
  })

  it('cleans up clipping planes on unmount', () => {
    const bbox = {
      min: { x: 0, y: 0, z: 0 },
      max: { x: 100, y: 100, z: 100 },
      getSize: vi.fn(() => ({ x: 100, y: 100, z: 100 })),
    }
    const { unmount } = render(<ClippingPlane axis="z" position={0.5} bbox={bbox} />)
    expect(mockGl.clippingPlanes).toHaveLength(1)
    unmount()
    expect(mockGl.clippingPlanes).toHaveLength(0)
  })

  it('handles null bbox gracefully', () => {
    render(<ClippingPlane axis="x" position={0.3} bbox={null} />)
    expect(mockGl.clippingPlanes).toHaveLength(1)
  })
})
