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
 *
 * geom-core 0.2.0 added what 0.1.0 could not report, and the suite compares
 * it too: `getBoundingBox()` min/max (0.1.0 returned extents only) against
 * stl-utils' and three.js's boxes, and `getSignedVolume()` against
 * printEstimator's tetrahedron sum before its `Math.abs`, with the same gates.
 */
import { describe, it, expect, afterAll } from 'vitest'
import { parseSTL, getBoundingBox } from '../stl-utils'
import { computeVolumeMm3, computeBoundingBox, computeCentroid } from '../printEstimator'
import { loadGeomCore, analyzeSTLBytes } from '../geomCoreBrowser'
import { computeGeomCoreMetrics } from '../meshMetrics'
import { MESH_FIXTURES, toBufferGeometry, toBinarySTL } from './meshFixtures'

/** printEstimator.computeVolumeMm3's sum, without its final Math.abs (the signed oracle). */
function signedVolumeOracle(geometry) {
  const pos = geometry.attributes.position
  const index = geometry.index
  const triCount = (index ? index.count : pos.count) / 3
  let volume = 0
  for (let i = 0; i < triCount; i++) {
    const [a, b, c] = [0, 1, 2].map((k) => (index ? index.getX(i * 3 + k) : i * 3 + k))
    const v0 = { x: pos.getX(a), y: pos.getY(a), z: pos.getZ(a) }
    const v1 = { x: pos.getX(b), y: pos.getY(b), z: pos.getZ(b) }
    const v2 = { x: pos.getX(c), y: pos.getY(c), z: pos.getZ(c) }
    volume += (
      v0.x * (v1.y * v2.z - v2.y * v1.z) -
      v1.x * (v0.y * v2.z - v2.y * v0.z) +
      v2.x * (v0.y * v1.z - v1.y * v0.z)
    ) / 6.0
  }
  return volume
}

/** geom-core 0.2.0 throws GeomCoreSTLError ("geom-core could not read the STL: <reason>"). */
function expectSTLError(fn) {
  let thrown = null
  try { fn() } catch (err) { thrown = err }
  expect(thrown).not.toBeNull()
  expect(thrown.name).toBe('GeomCoreSTLError')
  expect(thrown.message).toMatch(/^geom-core could not read the STL: \S/)
}

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

    describe('0.2.0 API: bbox min/max, signed volume, triangle indices', () => {
      for (const fixture of MESH_FIXTURES) {
        it(fixture.name, async () => {
          const buffer = toBinarySTL(fixture)
          const ts = parseSTL(buffer)
          const tsBox = getBoundingBox(ts.vertices)
          const mod = await loadGeomCore()
          const wasm = analyzeSTLBytes(mod, new Uint8Array(buffer))
          for (let k = 0; k < 3; k++) {
            expectLength(wasm.bbox.min[k], tsBox.min[k])
            expectLength(wasm.bbox.max[k], tsBox.max[k])
          }
          // three.js's box (what printEstimator.computeBoundingBox reads) agrees too.
          const geometry = toBufferGeometry(fixture)
          geometry.computeBoundingBox()
          const { min, max } = geometry.boundingBox
          ;[min.x, min.y, min.z].forEach((v, k) => expectLength(wasm.bbox.min[k], v))
          ;[max.x, max.y, max.z].forEach((v, k) => expectLength(wasm.bbox.max[k], v))

          expectVolume(wasm.signedVolumeMm3, signedVolumeOracle(geometry))
          expect(wasm.volumeMm3).toBe(Math.abs(wasm.signedVolumeMm3))

          // getIndices() is an owned copy of 3 corners per triangle the analyzer read.
          const analyzer = new mod.Analyzer()
          try {
            analyzer.loadSTLFromBytes(new Uint8Array(buffer))
            expect(analyzer.getIndices().length).toBe(3 * ts.faceCount)
            expect(analyzer.getVertices().length).toBe(3 * analyzer.getVertexCount())
          } finally {
            analyzer.delete()
          }
        })
      }

      it('an inside-out box has a negative signed volume and the same absolute volume', async () => {
        const inverted = MESH_FIXTURES.find((f) => f.name === 'box 1x2x3 inside out')
        const outward = MESH_FIXTURES.find((f) => f.name.startsWith('box 1x2x3 offset'))
        const mod = await loadGeomCore()
        const a = analyzeSTLBytes(mod, new Uint8Array(toBinarySTL(inverted)))
        const b = analyzeSTLBytes(mod, new Uint8Array(toBinarySTL(outward)))
        expect(a.signedVolumeMm3).toBeLessThan(0)
        expect(b.signedVolumeMm3).toBeGreaterThan(0)
        expectVolume(a.signedVolumeMm3, -b.signedVolumeMm3)
        expect(a.volumeMm3).toBe(Math.abs(a.signedVolumeMm3))
        expectVolume(a.volumeMm3, b.volumeMm3)
      })
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
        expectSTLError(() => analyzeSTLBytes(mod, new Uint8Array(buffer)))
      })

      it('both reject a buffer truncated below its declared face count', async () => {
        const buffer = new ArrayBuffer(84 + 10)
        new DataView(buffer).setUint32(80, 1, true)
        expect(() => parseSTL(buffer)).toThrow('buffer smaller than expected')
        const mod = await loadGeomCore()
        expectSTLError(() => analyzeSTLBytes(mod, new Uint8Array(buffer)))
      })

      it('both reject a header claiming more faces than the buffer holds (20M)', async () => {
        const buffer = new ArrayBuffer(84)
        new DataView(buffer).setUint32(80, 20_000_000, true)
        expect(() => parseSTL(buffer)).toThrow('face count exceeds')
        const mod = await loadGeomCore()
        expectSTLError(() => analyzeSTLBytes(mod, new Uint8Array(buffer)))
      })
    })
  })
}
