import { describe, it, expect } from 'vitest'
import { computeCreaseNormals, PREVIEW_CREASE_ANGLE_DEG, RENDER_CREASE_ANGLE_DEG } from './creaseNormals'

type Point = [number, number, number]

/** Float32 normals agree to about 1e-7, which `acos` turns into a few hundredths of a degree. */
const SAME_DIRECTION_DEG = 0.05

const soup = (triangles: Point[][]) => new Float32Array(triangles.flat(2))

/** The side wall of an n-sided prism around Z, two triangles per side, outward winding. */
function prismWall(sides: number, radius = 10, height = 5): Float32Array {
    const triangles: Point[][] = []
    for (let i = 0; i < sides; i++) {
        // The last side ends on the first side's own start point, bit for bit.
        const a0 = (i / sides) * Math.PI * 2, a1 = (((i + 1) % sides) / sides) * Math.PI * 2
        const p0: Point = [Math.cos(a0) * radius, Math.sin(a0) * radius, 0]
        const p1: Point = [Math.cos(a1) * radius, Math.sin(a1) * radius, 0]
        const q0: Point = [p0[0], p0[1], height], q1: Point = [p1[0], p1[1], height]
        triangles.push([p0, p1, q1], [p0, q1, q0])
    }
    return soup(triangles)
}

const normalAt = (normals: Float32Array, corner: number): Point =>
    [normals[corner * 3], normals[corner * 3 + 1], normals[corner * 3 + 2]]

const angleDeg = (a: Point, b: Point) =>
    (Math.acos(Math.min(1, Math.max(-1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]))) * 180) / Math.PI

/** Largest angle between a wall corner's normal and the true radial direction at that corner. */
function worstRadialError(positions: Float32Array, normals: Float32Array): number {
    let worst = 0
    for (let c = 0; c < positions.length / 3; c++) {
        const x = positions[c * 3], y = positions[c * 3 + 1]
        const r = Math.hypot(x, y)
        worst = Math.max(worst, angleDeg(normalAt(normals, c), [x / r, y / r, 0]))
    }
    return worst
}

describe('computeCreaseNormals', () => {
    it('keeps the edges of a box sharp', () => {
        // Two faces of a box meeting at 90° along the X axis.
        const positions = soup([
            [[0, 0, 0], [1, 0, 0], [1, 1, 0]], [[0, 0, 0], [1, 1, 0], [0, 1, 0]], // top, +Z
            [[0, 0, 0], [0, 0, -1], [1, 0, -1]], [[0, 0, 0], [1, 0, -1], [1, 0, 0]], // front, -Y
        ])
        const normals = computeCreaseNormals(positions, PREVIEW_CREASE_ANGLE_DEG)
        for (let c = 0; c < 6; c++) expect(angleDeg(normalAt(normals, c), [0, 0, 1])).toBeLessThan(SAME_DIRECTION_DEG)
        for (let c = 6; c < 12; c++) expect(angleDeg(normalAt(normals, c), [0, -1, 0])).toBeLessThan(SAME_DIRECTION_DEG)
    })

    it('shades a round wall as one surface', () => {
        const positions = prismWall(64)
        const normals = computeCreaseNormals(positions, RENDER_CREASE_ANGLE_DEG)
        expect(worstRadialError(positions, normals)).toBeLessThan(SAME_DIRECTION_DEG)
    })

    it('leaves the wall faceted when the crease angle is below the facet angle', () => {
        const positions = prismWall(64) // 5.6° between facets
        const normals = computeCreaseNormals(positions, 3)
        expect(worstRadialError(positions, normals)).toBeCloseTo(360 / 64 / 2, 1)
    })

    it('smooths a 20-sided circle and keeps a 16-sided one faceted in a render', () => {
        const round = prismWall(20), lowPoly = prismWall(16)
        expect(worstRadialError(round, computeCreaseNormals(round, RENDER_CREASE_ANGLE_DEG))).toBeLessThan(SAME_DIRECTION_DEG)
        expect(worstRadialError(lowPoly, computeCreaseNormals(lowPoly, RENDER_CREASE_ANGLE_DEG))).toBeCloseTo(11.25, 1)
    })

    it('smooths the uneven facets a decimated preview leaves on a round wall', () => {
        const coarse = prismWall(12) // 30° between facets
        expect(worstRadialError(coarse, computeCreaseNormals(coarse, PREVIEW_CREASE_ANGLE_DEG))).toBeLessThan(SAME_DIRECTION_DEG)
    })

    it('lets a large flat face keep its normal beside a thin strip', () => {
        const tilt = (10 * Math.PI) / 180
        const positions = soup([
            // A 100 x 100 flat face in the XY plane.
            [[0, 0, 0], [100, 0, 0], [100, 100, 0]], [[0, 0, 0], [100, 100, 0], [0, 100, 0]],
            // A strip 0.5 wide along its X = 0 edge, turned 10° downwards: the start of a fillet.
            [[0, 0, 0], [0, 100, 0], [-0.5 * Math.cos(tilt), 100, -0.5 * Math.sin(tilt)]],
            [[0, 0, 0], [-0.5 * Math.cos(tilt), 100, -0.5 * Math.sin(tilt)], [-0.5 * Math.cos(tilt), 0, -0.5 * Math.sin(tilt)]],
        ])
        const normals = computeCreaseNormals(positions, PREVIEW_CREASE_ANGLE_DEG)
        // Corner 0 is the flat face's corner on the shared edge.
        expect(angleDeg(normalAt(normals, 0), [0, 0, 1])).toBeLessThan(0.1)
        // The strip's corner on that edge follows the flat face too: the surfaces are tangent there.
        expect(angleDeg(normalAt(normals, 6), [0, 0, 1])).toBeLessThan(0.1)
    })

    it('gives a zero-area triangle a finite unit normal and no vote', () => {
        const positions = soup([
            [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
            [[0, 0, 0], [1, 0, 0], [2, 0, 0]], // collinear
            [[5, 5, 5], [5, 5, 5], [5, 5, 5]], // a single point
        ])
        const normals = computeCreaseNormals(positions, 30)
        expect([...normals].every(Number.isFinite)).toBe(true)
        for (let c = 0; c < 9; c++) expect(Math.hypot(...normalAt(normals, c))).toBeCloseTo(1, 5)
        for (let c = 0; c < 3; c++) expect(angleDeg(normalAt(normals, c), [0, 0, 1])).toBeLessThan(SAME_DIRECTION_DEG)
    })

    it('joins -0 and 0 as the same point', () => {
        const positions = soup([
            [[0, 0, 0], [1, 0, 0], [1, 1, 0.1]],
            [[-0, -0, -0], [1, 1, 0.1], [0, 1, 0]],
        ])
        const normals = computeCreaseNormals(positions, 30)
        // Both faces meet at the origin, so its two corners share one normal.
        expect(angleDeg(normalAt(normals, 0), normalAt(normals, 3))).toBeLessThan(SAME_DIRECTION_DEG)
    })

    it('reads a view that does not start at the beginning of its buffer', () => {
        const wall = prismWall(32)
        const padded = new Float32Array(wall.length + 3)
        padded.set(wall, 3)
        const fromView = computeCreaseNormals(padded.subarray(3), 20)
        expect([...fromView]).toEqual([...computeCreaseNormals(wall, 20)])
    })

    it('keeps flat normals at a point shared by thousands of faces', () => {
        // A cone: every side triangle meets at the apex.
        const sides = 2100
        const triangles: Point[][] = []
        for (let i = 0; i < sides; i++) {
            const a0 = (i / sides) * Math.PI * 2, a1 = (((i + 1) % sides) / sides) * Math.PI * 2
            triangles.push([[0, 0, 10], [Math.cos(a0) * 5, Math.sin(a0) * 5, 0], [Math.cos(a1) * 5, Math.sin(a1) * 5, 0]])
        }
        const positions = soup(triangles)
        const normals = computeCreaseNormals(positions, 30)
        // Apex corners keep their own face's normal (smoothed, they would lean 1.4° towards the
        // axis); rim corners are still smoothed.
        expect(angleDeg(normalAt(normals, 2), normalAt(normals, 4))).toBeLessThan(SAME_DIRECTION_DEG)
        const faceNormal = normalAt(computeCreaseNormals(positions.subarray(0, 9), 30), 0)
        expect(angleDeg(normalAt(normals, 0), faceNormal)).toBeLessThan(SAME_DIRECTION_DEG)
    })

    it('returns an empty result for an empty or partial input', () => {
        expect(computeCreaseNormals(new Float32Array(0), 30)).toHaveLength(0)
        expect([...computeCreaseNormals(new Float32Array(6), 30)]).toEqual([0, 0, 0, 0, 0, 0])
    })
})
