/**
 * Differential suite: geom-core WASM vs the Studio's TypeScript oracle.
 *
 * Tolerances (justification): every input coordinate is float32 and both
 * sides widen it to float64 before arithmetic, so the only differences are
 * summation order and geom-core's vertex welding. Observed worst cases on these fixtures: 2.6e-14 relative
 * (volume) and 1.4e-14 mm (lengths). The gates are
 *   volume   — 1e-9 relative (tightened from the brief's 1e-6; absolute
 *              1e-12 mm3 floor for zero-volume meshes)
 *   bbox     — 1e-9 mm absolute
 *   centroid — 1e-9 mm absolute
 * leaving ~5 orders of magnitude for summation-order growth on
 * million-triangle meshes,
 * and the suite also records the worst observed error so a regression that is
 * still inside the gate is visible in the test output.
 */
import { describe, it, expect, afterAll } from 'vitest'
import { parseSTL, getBoundingBox } from '../stl-utils'
import { computeVolumeMm3, computeBoundingBox, computeCentroid } from '../printEstimator'
import { loadGeomCore, analyzeSTLBytes } from '../geomCoreBrowser'
import { computeGeomCoreMetrics } from '../meshMetrics'
import { MESH_FIXTURES, toBufferGeometry, toBinarySTL } from './meshFixtures'

const VOLUME_REL = 1e-9
const VOLUME_ABS_FLOOR = 1e-12
const LENGTH_ABS = 1e-9

export function defineGeomCoreDifferentialSuite(environment) {
  const worst = { volumeRel: 0, lengthAbs: 0 }
  const track = (key, v) => { if (v > worst[key]) worst[key] = v }

  const expectVolume = (wasm, ts) => {
    const err = Math.abs(wasm - ts)
    const rel = ts === 0 ? err : err / Math.abs(ts)
    track('volumeRel', rel)
    expect(err).toBeLessThanOrEqual(Math.max(VOLUME_REL * Math.abs(ts), VOLUME_ABS_FLOOR))
  }
  const expectLength = (wasm, ts) => {
    const err = Math.abs(wasm - ts)
    track('lengthAbs', err)
    expect(err).toBeLessThanOrEqual(LENGTH_ABS)
  }

  describe(`geom-core WASM vs TypeScript oracle (${environment} environment)`, () => {
    afterAll(() => {
      console.info(`[geom-core differential, ${environment}] worst volume rel err ${worst.volumeRel.toExponential(2)}, worst length abs err ${worst.lengthAbs.toExponential(2)} mm`)
    })

    it('loads the real WASM module', async () => {
      const mod = await loadGeomCore()
      expect(typeof mod.Analyzer).toBe('function')
    })

    describe('printEstimator: volume / bbox / centroid', () => {
      for (const fixture of MESH_FIXTURES) {
        it(fixture.name, async () => {
          const geometry = toBufferGeometry(fixture)
          const wasm = await computeGeomCoreMetrics(geometry)
          expectVolume(wasm.volumeMm3, computeVolumeMm3(geometry))
          const tsBox = computeBoundingBox(geometry)
          expectLength(wasm.boundingBox.width, tsBox.width)
          expectLength(wasm.boundingBox.depth, tsBox.depth)
          expectLength(wasm.boundingBox.height, tsBox.height)
          const tsC = computeCentroid(geometry)
          expectLength(wasm.centroid.x, tsC.x)
          expectLength(wasm.centroid.y, tsC.y)
          expectLength(wasm.centroid.z, tsC.z)
        })
      }
    })

    describe('stl-utils: parse face count / bbox extents', () => {
      for (const fixture of MESH_FIXTURES) {
        it(fixture.name, async () => {
          const buffer = toBinarySTL(fixture)
          const ts = parseSTL(buffer)
          const tsBox = getBoundingBox(ts.vertices)
          const wasm = analyzeSTLBytes(await loadGeomCore(), new Uint8Array(buffer))
          expect(wasm.faceCount).toBe(ts.faceCount)
          for (let k = 0; k < 3; k++) expectLength(wasm.size[k], tsBox.size[k])
        })
      }

      it('both reject a buffer smaller than the 84-byte header', async () => {
        const buffer = new ArrayBuffer(10)
        expect(() => parseSTL(buffer)).toThrow('buffer too small')
        const mod = await loadGeomCore()
        expect(() => analyzeSTLBytes(mod, new Uint8Array(buffer))).toThrow(/could not read the STL/)
      })

      it('both reject a buffer truncated below its declared face count', async () => {
        const buffer = new ArrayBuffer(84 + 10)
        new DataView(buffer).setUint32(80, 1, true)
        expect(() => parseSTL(buffer)).toThrow('buffer smaller than expected')
        const mod = await loadGeomCore()
        expect(() => analyzeSTLBytes(mod, new Uint8Array(buffer))).toThrow(/could not read the STL/)
      })

      it('both reject a header claiming more faces than the buffer holds (20M)', async () => {
        const buffer = new ArrayBuffer(84)
        new DataView(buffer).setUint32(80, 20_000_000, true)
        expect(() => parseSTL(buffer)).toThrow('face count exceeds')
        const mod = await loadGeomCore()
        expect(() => analyzeSTLBytes(mod, new Uint8Array(buffer))).toThrow(/could not read the STL/)
      })
    })
  })
}
