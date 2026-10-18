/**
 * Mesh fixtures shared by the geom-core differential suite and the flag-off
 * identity test. The first six reproduce, coordinate for coordinate, the
 * fixtures of stl-utils.test.js and printEstimator.test.js; the rest widen the
 * differential to offset, inverted, multi-body, curved and sub-threshold meshes.
 */
import * as THREE from 'three'

/** Axis-aligned box as 12 outward-wound triangles (flip = inside out). */
function boxTriangles([sx, sy, sz], [ox, oy, oz] = [0, 0, 0], flip = false) {
  const p = [[0, 0, 0], [sx, 0, 0], [sx, sy, 0], [0, sy, 0], [0, 0, sz], [sx, 0, sz], [sx, sy, sz], [0, sy, sz]]
    .map(([x, y, z]) => [x + ox, y + oy, z + oz])
  const f = [[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]]
  return f.flatMap((t) => (flip ? [t[0], t[2], t[1]] : t).flatMap((i) => p[i]))
}

/** UV sphere, outward wound, as a triangle soup. */
function sphereTriangles(r, [cx, cy, cz], seg = 48, rings = 24) {
  const pt = (i, j) => {
    const th = (Math.PI * j) / rings
    const ph = (2 * Math.PI * i) / seg
    return [cx + r * Math.sin(th) * Math.cos(ph), cy + r * Math.sin(th) * Math.sin(ph), cz + r * Math.cos(th)]
  }
  const out = []
  for (let j = 0; j < rings; j++) {
    for (let i = 0; i < seg; i++) {
      const a = pt(i, j), b = pt(i + 1, j), c = pt(i + 1, j + 1), d = pt(i, j + 1)
      if (j !== 0) out.push(...a, ...d, ...b)
      if (j !== rings - 1) out.push(...b, ...d, ...c)
    }
  }
  return out
}

const TETRA_UNIT = [
  0, 0, 0, 1, 0, 0, 0, 1, 0,
  0, 0, 0, 1, 0, 0, 0, 0, 1,
  0, 0, 0, 0, 1, 0, 0, 0, 1,
  1, 0, 0, 0, 1, 0, 0, 0, 1,
]

/** @type {{ name: string, positions: number[], index?: number[] }[]} */
export const MESH_FIXTURES = [
  // stl-utils.test.js: makeSTLBuffer(1) / getBoundingBox known vertices
  { name: 'stl-utils: single triangle at origin', positions: [0, 0, 0, 1, 0, 0, 0, 1, 0] },
  // printEstimator.test.js: computeVolumeMm3 / computeCentroid unit tetrahedron (mixed winding)
  { name: 'printEstimator: unit tetrahedron (non-indexed)', positions: TETRA_UNIT },
  // printEstimator.test.js: indexed tetrahedron, edge 10
  {
    name: 'printEstimator: indexed tetrahedron (edge 10)',
    positions: [0, 0, 0, 10, 0, 0, 0, 10, 0, 0, 0, 10],
    index: [0, 1, 2, 0, 1, 3, 0, 2, 3, 1, 2, 3],
  },
  // printEstimator.test.js: computeBoundingBox min (-5,-10,0) max (15,10,30) as a solid
  { name: 'printEstimator: bbox fixture as a 20x20x30 box', positions: boxTriangles([20, 20, 30], [-5, -10, 0]) },
  // printEstimator.test.js: "cube" fixture (offset tetrahedron at 10..11)
  {
    name: 'printEstimator: offset tetrahedron at (10,10,10)',
    positions: [
      10, 10, 10, 10, 11, 10, 11, 10, 10,
      10, 10, 10, 11, 10, 10, 10, 10, 11,
      10, 10, 10, 10, 10, 11, 10, 11, 10,
      11, 10, 10, 10, 11, 10, 10, 10, 11,
    ],
  },
  // printEstimator.test.js: degenerate geometry — no volume
  { name: 'printEstimator: two coplanar triangles (zero volume)', positions: [0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0] },
  // Wider coverage
  { name: 'box 1x2x3 offset to (10,-5,7)', positions: boxTriangles([1, 2, 3], [10, -5, 7]) },
  { name: 'box 1x2x3 inside out', positions: boxTriangles([1, 2, 3], [10, -5, 7], true) },
  { name: 'two bodies (unit cubes 5 mm apart)', positions: [...boxTriangles([1, 1, 1]), ...boxTriangles([1, 1, 1], [5, 0, 0])] },
  { name: 'UV sphere r=12.5 at (3.3,-7.1,20.25), 2208 triangles', positions: sphereTriangles(12.5, [3.3, -7.1, 20.25]) },
  { name: 'sub-threshold box (1e-12 mm3, centroid rule)', positions: boxTriangles([1e-4, 1e-4, 1e-4], [0.1, 0.1, 0.1]) },
]

/** Real THREE.BufferGeometry — the type the viewer hands to printEstimator. */
export function toBufferGeometry(fixture) {
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.Float32BufferAttribute(fixture.positions, 3))
  if (fixture.index) g.setIndex(fixture.index)
  return g
}

/** Binary STL bytes for a fixture (float32 coordinates, zero normals). */
export function toBinarySTL(fixture) {
  const indexed = toBufferGeometry(fixture)
  const g = fixture.index ? indexed.toNonIndexed() : indexed
  const pos = g.attributes.position
  const faces = pos.count / 3
  const buf = new ArrayBuffer(84 + faces * 50)
  const view = new DataView(buf)
  view.setUint32(80, faces, true)
  let o = 84
  for (let i = 0; i < pos.count; i++) {
    if (i % 3 === 0) o += 12
    view.setFloat32(o, pos.getX(i), true); o += 4
    view.setFloat32(o, pos.getY(i), true); o += 4
    view.setFloat32(o, pos.getZ(i), true); o += 4
    if (i % 3 === 2) o += 2
  }
  return buf
}
