import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

vi.mock('@react-three/drei', () => ({
  Line: ({ points }) => <div data-testid="line" data-points={JSON.stringify(points)} />,
  Html: ({ children, position }) => <div data-testid="html-label" data-position={JSON.stringify(position)}>{children}</div>,
  Cone: () => null,
}))

vi.mock('three', () => ({
  Vector3: function(x, y, z) { this.x = x || 0; this.y = y || 0; this.z = z || 0 },
}))

import AxisScaleHint from './AxisScaleHint'

const makeBox = (minX = 0, maxX = 100, minY = 0, maxY = 100, minZ = 0, maxZ = 50) => ({
  min: { x: minX, y: minY, z: minZ, toArray: () => [minX, minY, minZ] },
  max: { x: maxX, y: maxY, z: maxZ, toArray: () => [maxX, maxY, maxZ] },
})

describe('AxisScaleHint', () => {
  it('renders range labels for X axis', () => {
    const param = {
      paramId: 'width',
      paramDef: { id: 'width', type: 'slider', min: 1, max: 10, label: { en: 'Width' } },
      currentValue: 5,
      hint: { type: 'axis_scale', axis: 'x', affected_parts: ['cup'] },
    }
    render(<AxisScaleHint param={param} bbox={makeBox()} centerOfMass={[50, 50, 25]} />)
    // Should render min (1) and max (10) labels
    expect(screen.getByText('1')).toBeTruthy()
    expect(screen.getByText('10')).toBeTruthy()
  })

  it('renders range labels for Z axis', () => {
    const param = {
      paramId: 'height',
      paramDef: { id: 'height', type: 'slider', min: 0, max: 20, label: { en: 'Height' } },
      currentValue: 10,
      hint: { type: 'axis_scale', axis: 'z', affected_parts: ['cup'] },
    }
    render(<AxisScaleHint param={param} bbox={makeBox()} centerOfMass={[50, 50, 25]} />)
    expect(screen.getByText('0')).toBeTruthy()
    expect(screen.getByText('20')).toBeTruthy()
  })

  it('renders dashed line between start and end', () => {
    const param = {
      paramId: 'depth',
      paramDef: { id: 'depth', type: 'slider', min: 5, max: 50, label: { en: 'Depth' } },
      currentValue: 20,
      hint: { type: 'axis_scale', axis: 'y', affected_parts: ['cup'] },
    }
    render(<AxisScaleHint param={param} bbox={makeBox()} centerOfMass={[50, 50, 25]} />)
    const lines = screen.getAllByTestId('line')
    expect(lines.length).toBeGreaterThanOrEqual(1)
  })

  it('returns null when bbox is null', () => {
    const param = {
      paramId: 'width',
      paramDef: { id: 'width', type: 'slider', min: 1, max: 10, label: { en: 'Width' } },
      currentValue: 5,
      hint: { type: 'axis_scale', axis: 'x', affected_parts: ['cup'] },
    }
    const { container } = render(<AxisScaleHint param={param} bbox={null} centerOfMass={[0, 0, 0]} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders radial hint for radial axis', () => {
    const param = {
      paramId: 'diameter',
      paramDef: { id: 'diameter', type: 'slider', min: 5, max: 50, label: { en: 'Diameter' } },
      currentValue: 20,
      hint: { type: 'axis_scale', axis: 'radial', affected_parts: ['ring'] },
    }
    render(<AxisScaleHint param={param} bbox={makeBox()} centerOfMass={[50, 50, 25]} />)
    // Radial hint renders circle lines + labels
    expect(screen.getByText('5')).toBeTruthy()
    expect(screen.getByText('50')).toBeTruthy()
  })

  it('returns null for unknown axis', () => {
    const param = {
      paramId: 'custom',
      paramDef: { id: 'custom', type: 'slider', min: 0, max: 10, label: { en: 'Custom' } },
      currentValue: 5,
      hint: { type: 'axis_scale', axis: 'w', affected_parts: [] },
    }
    const { container } = render(<AxisScaleHint param={param} bbox={makeBox()} centerOfMass={[0, 0, 0]} />)
    expect(container.innerHTML).toBe('')
  })

  it('handles decimal values in range labels', () => {
    const param = {
      paramId: 'thickness',
      paramDef: { id: 'thickness', type: 'slider', min: 0.5, max: 3.5, label: { en: 'Thickness' } },
      currentValue: 1.5,
      hint: { type: 'axis_scale', axis: 'x', affected_parts: ['wall'] },
    }
    render(<AxisScaleHint param={param} bbox={makeBox()} centerOfMass={[50, 50, 25]} />)
    expect(screen.getByText('0.5')).toBeTruthy()
    expect(screen.getByText('3.5')).toBeTruthy()
  })

  it('sets aria-hidden on the root group', () => {
    const param = {
      paramId: 'width',
      paramDef: { id: 'width', type: 'slider', min: 1, max: 10, label: { en: 'Width' } },
      currentValue: 5,
      hint: { type: 'axis_scale', axis: 'x', affected_parts: ['cup'] },
    }
    const { container } = render(<AxisScaleHint param={param} bbox={makeBox()} centerOfMass={[50, 50, 25]} />)
    // The root group should have aria-hidden
    const root = container.firstChild
    expect(root.getAttribute('aria-hidden')).toBe('true')
  })
})
