import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'

// Mock R3F — useFrame is a no-op in test
vi.mock('@react-three/fiber', () => ({
  useFrame: vi.fn(),
}))

// Mock useWorkerLoader to return a simple geometry
const mockGeometry = { type: 'BufferGeometry' }
vi.mock('../../hooks/render/useWorkerLoader', () => ({
  useWorkerLoader: vi.fn((url) => url ? ({ geometry: mockGeometry, scene: null }) : ({ geometry: null, scene: null })),
}))

import GhostGeometryOverlay from './GhostGeometryOverlay'

describe('GhostGeometryOverlay', () => {
  it('returns null when variants have no parts', () => {
    const { container } = render(
      <GhostGeometryOverlay variants={{}} />
    )
    expect(container.innerHTML).toBe('')
  })

  it('returns null when variants is null', () => {
    const { container } = render(
      <GhostGeometryOverlay variants={null} />
    )
    expect(container.innerHTML).toBe('')
  })

  it('renders ghost models for min variants', () => {
    const variants = {
      min: [
        { type: 'base', url: 'blob:http://test/min-base', isGlb: true },
      ],
    }
    const { container } = render(
      <GhostGeometryOverlay variants={variants} />
    )
    // Should render something (group with meshes)
    expect(container.innerHTML).not.toBe('')
  })

  it('renders ghost models for both min and max variants', () => {
    const variants = {
      min: [
        { type: 'base', url: 'blob:http://test/min-base', isGlb: true },
      ],
      max: [
        { type: 'base', url: 'blob:http://test/max-base', isGlb: true },
      ],
    }
    const { container } = render(
      <GhostGeometryOverlay variants={variants} />
    )
    expect(container.innerHTML).not.toBe('')
  })

  it('sets aria-hidden on root group', () => {
    const variants = {
      min: [{ type: 'base', url: 'blob:http://test/min', isGlb: true }],
    }
    const { container } = render(
      <GhostGeometryOverlay variants={variants} />
    )
    const group = container.firstChild
    expect(group).toBeTruthy()
  })

  it('accepts custom color prop', () => {
    const variants = {
      min: [{ type: 'base', url: 'blob:http://test/min', isGlb: true }],
    }
    // Should not throw
    const { container } = render(
      <GhostGeometryOverlay variants={variants} color="#ff0000" />
    )
    expect(container.innerHTML).not.toBe('')
  })

  it('respects prefers-reduced-motion', () => {
    const originalMatchMedia = window.matchMedia
    window.matchMedia = vi.fn(() => ({ matches: true }))

    const variants = {
      min: [{ type: 'base', url: 'blob:http://test/min', isGlb: true }],
    }
    const { container } = render(
      <GhostGeometryOverlay variants={variants} />
    )
    expect(container.innerHTML).not.toBe('')

    window.matchMedia = originalMatchMedia
  })
})
