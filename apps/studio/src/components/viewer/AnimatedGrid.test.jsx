import { describe, it, expect } from 'vitest'

// AnimatedGrid is a Three.js/R3F component that can't render in jsdom,
// so we test the grid positioning logic directly.

/** Mirrors the gridPitch formula from AnimatedGrid.jsx */
function gridPitch(size, rotationClearance) {
  return size * Math.SQRT2 + rotationClearance
}

/** Mirrors the per-cube position computation from AnimatedGrid.jsx */
function cubePosition(r, c, size, rotationClearance, tubingH = 0, center = { x: 0, y: 0, z: 0 }) {
  const pitch = gridPitch(size, rotationClearance)
  return {
    x: center.x,
    y: c * pitch + center.y,
    z: r * (size + tubingH) + tubingH + center.z,
  }
}

describe('AnimatedGrid positioning logic', () => {
  describe('gridPitch formula', () => {
    it('computes size * √2 + rotationClearance (defaults)', () => {
      const pitch = gridPitch(20, 2)
      expect(pitch).toBeCloseTo(20 * Math.SQRT2 + 2)
    })

    it('scales with size', () => {
      const small = gridPitch(10, 2)
      const large = gridPitch(40, 2)
      expect(large).toBeCloseTo(small * 4 - 2 * 3) // 40√2+2 vs 10√2+2
      // Simpler: just verify the formula
      expect(large).toBeCloseTo(40 * Math.SQRT2 + 2)
    })

    it('respects custom rotation_clearance', () => {
      const pitch = gridPitch(20, 5)
      expect(pitch).toBeCloseTo(20 * Math.SQRT2 + 5)
    })
  })

  describe('grid position computation', () => {
    it('columns spread along Y axis', () => {
      const p0 = cubePosition(0, 0, 20, 2)
      const p1 = cubePosition(0, 1, 20, 2)
      const p2 = cubePosition(0, 2, 20, 2)

      const pitch = gridPitch(20, 2)
      expect(p0.y).toBeCloseTo(0)
      expect(p1.y).toBeCloseTo(pitch)
      expect(p2.y).toBeCloseTo(2 * pitch)
      // X and Z unchanged across columns in the same row
      expect(p0.z).toBeCloseTo(p1.z)
      expect(p0.x).toBeCloseTo(p1.x)
    })

    it('rows stack along Z axis with tubing spacers', () => {
      const tubingH = 2
      const p0 = cubePosition(0, 0, 20, 2, tubingH)
      const p1 = cubePosition(1, 0, 20, 2, tubingH)
      const p2 = cubePosition(2, 0, 20, 2, tubingH)

      // z = r * (size + tubingH) + tubingH
      expect(p0.z).toBeCloseTo(2)       // 0*(20+2)+2
      expect(p1.z).toBeCloseTo(24)      // 1*(20+2)+2
      expect(p2.z).toBeCloseTo(46)      // 2*(20+2)+2
      // Y unchanged across rows in the same column
      expect(p0.y).toBeCloseTo(p1.y)
    })

    it('single cell (1×1) sits at the center offset', () => {
      const center = { x: 5, y: 10, z: 15 }
      const pos = cubePosition(0, 0, 20, 2, 0, center)
      expect(pos.x).toBeCloseTo(5)
      expect(pos.y).toBeCloseTo(10)
      expect(pos.z).toBeCloseTo(15)
    })

    it('applies geometry center offset to all cells', () => {
      const center = { x: 1, y: 2, z: 3 }
      const pitch = gridPitch(20, 2)
      // tubingH = 0: flush stacking
      const pos = cubePosition(1, 2, 20, 2, 0, center)
      expect(pos.x).toBeCloseTo(1)
      expect(pos.y).toBeCloseTo(2 * pitch + 2)
      expect(pos.z).toBeCloseTo(1 * 20 + 0 + 3)

      // tubingH = 2: spacer gaps
      const pos2 = cubePosition(1, 2, 20, 2, 2, center)
      expect(pos2.z).toBeCloseTo(1 * (20 + 2) + 2 + 3) // 27
    })

    it('tubingH defaults to 0 (flush stacking)', () => {
      // Omit tubingH — should behave like tubingH=0
      const p0 = cubePosition(0, 0, 20, 2)
      const p1 = cubePosition(1, 0, 20, 2)
      const p2 = cubePosition(2, 0, 20, 2)

      expect(p0.z).toBeCloseTo(0)   // 0*(20+0)+0
      expect(p1.z).toBeCloseTo(20)  // 1*(20+0)+0
      expect(p2.z).toBeCloseTo(40)  // 2*(20+0)+0
    })
  })

  describe('defaults', () => {
    it('default size=20 and rotation_clearance=2 match component', () => {
      const size = 20
      const rotationClearance = 2
      const pitch = gridPitch(size, rotationClearance)
      expect(pitch).toBeCloseTo(20 * Math.SQRT2 + 2)
    })
  })
})
