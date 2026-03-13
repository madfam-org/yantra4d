import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'

vi.mock('@react-three/drei', () => ({
  Line: () => null,
  Html: ({ children }) => <div>{children}</div>,
  Cone: () => null,
}))

vi.mock('three', () => ({
  Vector3: function(x, y, z) { this.x = x || 0; this.y = y || 0; this.z = z || 0 },
}))

import ParameterPreviewOverlay from './ParameterPreviewOverlay'

const makeBox = () => ({
  min: { x: 0, y: 0, z: 0, toArray: () => [0, 0, 0] },
  max: { x: 100, y: 100, z: 50, toArray: () => [100, 100, 50] },
})

describe('ParameterPreviewOverlay', () => {
  it('returns null when hoveredParam is null', () => {
    const { container } = render(
      <ParameterPreviewOverlay hoveredParam={null} sceneBox={makeBox()} centerOfMass={[50, 50, 25]} />
    )
    expect(container.innerHTML).toBe('')
  })

  it('returns null when sceneBox is null', () => {
    const hoveredParam = {
      paramId: 'width',
      paramDef: { id: 'width', type: 'slider', min: 1, max: 10, label: { en: 'Width' } },
      currentValue: 5,
      hint: { type: 'axis_scale', axis: 'x', affected_parts: ['cup'] },
    }
    const { container } = render(
      <ParameterPreviewOverlay hoveredParam={hoveredParam} sceneBox={null} centerOfMass={[0, 0, 0]} />
    )
    expect(container.innerHTML).toBe('')
  })

  it('renders AxisScaleHint for axis_scale hint type', () => {
    const hoveredParam = {
      paramId: 'width',
      paramDef: { id: 'width', type: 'slider', min: 1, max: 10, label: { en: 'Width' } },
      currentValue: 5,
      hint: { type: 'axis_scale', axis: 'x', affected_parts: ['cup'] },
    }
    const { container } = render(
      <ParameterPreviewOverlay hoveredParam={hoveredParam} sceneBox={makeBox()} centerOfMass={[50, 50, 25]} />
    )
    // AxisScaleHint renders, so container should have content (range labels)
    expect(container.innerHTML).not.toBe('')
  })

  it('returns null for part_highlight hint type (handled elsewhere)', () => {
    const hoveredParam = {
      paramId: 'quality',
      paramDef: { id: 'quality', type: 'slider', min: 1, max: 100, label: { en: 'Quality' } },
      currentValue: 50,
      hint: { type: 'part_highlight', affected_parts: ['cup'] },
    }
    const { container } = render(
      <ParameterPreviewOverlay hoveredParam={hoveredParam} sceneBox={makeBox()} centerOfMass={[0, 0, 0]} />
    )
    expect(container.innerHTML).toBe('')
  })

  it('returns null for toggle_highlight hint type', () => {
    const hoveredParam = {
      paramId: 'magnets',
      paramDef: { id: 'magnets', type: 'checkbox', label: { en: 'Magnets' } },
      currentValue: true,
      hint: { type: 'toggle_highlight', affected_parts: ['cup'] },
    }
    const { container } = render(
      <ParameterPreviewOverlay hoveredParam={hoveredParam} sceneBox={makeBox()} centerOfMass={[0, 0, 0]} />
    )
    expect(container.innerHTML).toBe('')
  })

  it('returns null for none hint type', () => {
    const hoveredParam = {
      paramId: 'color',
      paramDef: { id: 'color', type: 'color', label: { en: 'Color' } },
      currentValue: '#ff0000',
      hint: { type: 'none' },
    }
    const { container } = render(
      <ParameterPreviewOverlay hoveredParam={hoveredParam} sceneBox={makeBox()} centerOfMass={[0, 0, 0]} />
    )
    expect(container.innerHTML).toBe('')
  })
})
