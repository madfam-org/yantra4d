import { describe, it, expect } from 'vitest'
import { computeVolumeMm3, computeBoundingBox, estimatePrint, getMaterialProfiles } from './printEstimator'

describe('printEstimator', () => {
  describe('computeVolumeMm3', () => {
    it('returns 0 for null geometry', () => {
      expect(computeVolumeMm3(null)).toBe(0)
    })

    it('returns 0 for geometry without position attribute', () => {
      expect(computeVolumeMm3({ attributes: {} })).toBe(0)
    })

    it('computes volume of a simple tetrahedron', () => {
      // A tetrahedron with vertices at:
      // (0,0,0), (1,0,0), (0,1,0), (0,0,1)
      // Volume = 1/6
      const positions = new Float32Array([
        // Face 1: (0,0,0), (1,0,0), (0,1,0)
        0, 0, 0, 1, 0, 0, 0, 1, 0,
        // Face 2: (0,0,0), (1,0,0), (0,0,1)
        0, 0, 0, 1, 0, 0, 0, 0, 1,
        // Face 3: (0,0,0), (0,1,0), (0,0,1)
        0, 0, 0, 0, 1, 0, 0, 0, 1,
        // Face 4: (1,0,0), (0,1,0), (0,0,1)
        1, 0, 0, 0, 1, 0, 0, 0, 1,
      ])

      const geometry = {
        attributes: {
          position: {
            count: 12,
            getX: (i) => positions[i * 3],
            getY: (i) => positions[i * 3 + 1],
            getZ: (i) => positions[i * 3 + 2],
          }
        },
        index: null,
      }

      const volume = computeVolumeMm3(geometry)
      // Volume of unit tetrahedron = 1/6 ≈ 0.1667
      expect(volume).toBeCloseTo(1 / 6, 2)
    })

    it('computes volume with indexed geometry', () => {
      const positions = new Float32Array([
        0, 0, 0,  // 0
        10, 0, 0, // 1
        0, 10, 0, // 2
        0, 0, 10, // 3
      ])
      const indices = new Uint16Array([
        0, 1, 2,
        0, 1, 3,
        0, 2, 3,
        1, 2, 3,
      ])

      const geometry = {
        attributes: {
          position: {
            count: 4,
            getX: (i) => positions[i * 3],
            getY: (i) => positions[i * 3 + 1],
            getZ: (i) => positions[i * 3 + 2],
          }
        },
        index: {
          count: 12,
          getX: (i) => indices[i],
        },
      }

      const volume = computeVolumeMm3(geometry)
      // Volume of tetrahedron with edge 10 = 10^3/6 ≈ 166.67
      expect(volume).toBeCloseTo(1000 / 6, 0)
    })
  })

  describe('computeBoundingBox', () => {
    it('returns zeros for null geometry', () => {
      expect(computeBoundingBox(null)).toEqual({ width: 0, depth: 0, height: 0 })
    })

    it('computes bounding box dimensions', () => {
      const geometry = {
        computeBoundingBox: function () {
          this.boundingBox = {
            min: { x: -5, y: -10, z: 0 },
            max: { x: 15, y: 10, z: 30 },
          }
        },
        boundingBox: null,
      }

      const bbox = computeBoundingBox(geometry)
      expect(bbox.width).toBe(20)   // x range
      expect(bbox.depth).toBe(20)   // y range
      expect(bbox.height).toBe(30)  // z range (Z-up)
    })
  })

  describe('estimatePrint', () => {
    const volumeMm3 = 10000 // 10 cm³
    const bbox = { width: 30, depth: 30, height: 20 }

    it('returns time, filament, and material for PLA', () => {
      const result = estimatePrint(volumeMm3, bbox, 'pla')
      expect(result.material).toBe('PLA')
      expect(result.time).toHaveProperty('hours')
      expect(result.time).toHaveProperty('minutes')
      expect(result.filament).toHaveProperty('grams')
      expect(result.filament).toHaveProperty('meters')
      expect(result.filament).toHaveProperty('cost')
    })

    it('calculates positive filament weight', () => {
      const result = estimatePrint(volumeMm3, bbox, 'pla')
      expect(result.filament.grams).toBeGreaterThan(0)
      expect(result.filament.meters).toBeGreaterThan(0)
      expect(result.filament.cost).toBeGreaterThan(0)
    })

    it('PLA is denser than ABS', () => {
      const pla = estimatePrint(volumeMm3, bbox, 'pla')
      const abs = estimatePrint(volumeMm3, bbox, 'abs')
      expect(pla.filament.grams).toBeGreaterThan(abs.filament.grams)
    })

    it('higher infill increases weight', () => {
      const low = estimatePrint(volumeMm3, bbox, 'pla', { infill: 0.10 })
      const high = estimatePrint(volumeMm3, bbox, 'pla', { infill: 0.50 })
      expect(high.filament.grams).toBeGreaterThan(low.filament.grams)
    })

    it('falls back to PLA for unknown material', () => {
      const result = estimatePrint(volumeMm3, bbox, 'unknown_material')
      expect(result.material).toBe('PLA')
    })

    it('respects speed override', () => {
      const slow = estimatePrint(volumeMm3, bbox, 'pla', { speed: 20 })
      const fast = estimatePrint(volumeMm3, bbox, 'pla', { speed: 100 })
      const slowTotal = slow.time.hours * 60 + slow.time.minutes
      const fastTotal = fast.time.hours * 60 + fast.time.minutes
      expect(slowTotal).toBeGreaterThan(fastTotal)
    })
  })

  describe('getMaterialProfiles', () => {
    it('returns array of material profiles', () => {
      const profiles = getMaterialProfiles()
      expect(profiles.length).toBeGreaterThanOrEqual(4)
      expect(profiles.find(p => p.id === 'pla')).toBeTruthy()
      expect(profiles.find(p => p.id === 'petg')).toBeTruthy()
      expect(profiles.find(p => p.id === 'abs')).toBeTruthy()
      expect(profiles.find(p => p.id === 'tpu')).toBeTruthy()
    })

    it('each profile has id and name', () => {
      const profiles = getMaterialProfiles()
      for (const p of profiles) {
        expect(p.id).toBeTruthy()
        expect(p.name).toBeTruthy()
      }
    })
  })
})
