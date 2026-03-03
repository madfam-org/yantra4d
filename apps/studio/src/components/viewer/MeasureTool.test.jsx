import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Vector3 } from 'three'

const mockGlDomElement = {
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  getBoundingClientRect: vi.fn(() => ({ left: 0, top: 0, width: 800, height: 600 })),
}

vi.mock('@react-three/fiber', () => ({
  useThree: () => ({
    raycaster: { setFromCamera: vi.fn(), intersectObjects: vi.fn(() => []) },
    camera: {},
    scene: { children: [] },
    gl: { domElement: mockGlDomElement },
  }),
}))

vi.mock('@react-three/drei', () => ({
  Html: ({ children }) => <div data-testid="html-label">{children}</div>,
}))

vi.mock('three', () => {
  class Vector2 {
    constructor(x = 0, y = 0) { this.x = x; this.y = y }
  }
  class Vector3 {
    constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z }
    clone() { return new Vector3(this.x, this.y, this.z) }
    distanceTo(other) { return Math.sqrt((this.x - other.x) ** 2 + (this.y - other.y) ** 2 + (this.z - other.z) ** 2) }
    lerpVectors(a, b, t) { this.x = a.x + (b.x - a.x) * t; this.y = a.y + (b.y - a.y) * t; this.z = a.z + (b.z - a.z) * t; return this }
  }
  return { Vector2, Vector3 }
})

import MeasureTool from './MeasureTool'

describe('MeasureTool', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('adds click listener when active', () => {
    render(<MeasureTool active={true} onMeasure={vi.fn()} measurements={[]} />)
    expect(mockGlDomElement.addEventListener).toHaveBeenCalledWith('click', expect.any(Function))
  })

  it('removes click listener on unmount', () => {
    const { unmount } = render(<MeasureTool active={true} onMeasure={vi.fn()} measurements={[]} />)
    unmount()
    expect(mockGlDomElement.removeEventListener).toHaveBeenCalledWith('click', expect.any(Function))
  })

  it('does not add click listener when not active', () => {
    render(<MeasureTool active={false} onMeasure={vi.fn()} measurements={[]} />)
    expect(mockGlDomElement.addEventListener).not.toHaveBeenCalled()
  })

  it('renders completed measurements with distance labels', () => {

    const measurements = [
      { a: new Vector3(0, 0, 0), b: new Vector3(10, 0, 0), distance: 10 },
    ]
    render(<MeasureTool active={true} onMeasure={vi.fn()} measurements={measurements} />)
    expect(screen.getByText('10.00mm')).toBeInTheDocument()
  })

  it('renders multiple measurements', () => {

    const measurements = [
      { a: new Vector3(0, 0, 0), b: new Vector3(10, 0, 0), distance: 10 },
      { a: new Vector3(0, 0, 0), b: new Vector3(0, 25, 0), distance: 25 },
    ]
    render(<MeasureTool active={true} onMeasure={vi.fn()} measurements={measurements} />)
    expect(screen.getByText('10.00mm')).toBeInTheDocument()
    expect(screen.getByText('25.00mm')).toBeInTheDocument()
  })
})
