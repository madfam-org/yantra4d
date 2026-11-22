/**
 * Crease-angle normals for a triangle soup.
 *
 * The models pipeline writes positions only (docs/guides/landing-models-pipeline.md). Drawn
 * flat-shaded every triangle is its own patch and a decimated preview shows every facet. Here
 * each corner gets the mean of the faces that meet at its point and lie within the crease angle
 * of its own face, so a cylinder shades as one surface while a box edge stays an edge.
 *
 * Each face votes with its area times its angle at that corner. Area matters because CAD
 * tessellation puts a fan of large triangles on a flat face next to thin strips on a fillet:
 * the flat face then keeps its own normal and the fillet takes up the turn, where an even vote
 * tilts the flat face's rim and smears that tilt across the face as a streak. The angle matters
 * because a wall of quads cut by one diagonal has two triangles at one end of each edge and one
 * at the other; by area alone every normal on a cylinder leans towards the side with two.
 *
 * Twin: `apps/studio/src/lib/creaseNormals.ts` (the Studio is its own package). Keep the two in
 * step; `computeCreaseNormals` is the same code in both.
 */

/**
 * Facets further apart than this stay edges. The gallery draws the prerendered preview, which is
 * decimated to a triangle budget; that leaves round features with uneven facets, most of them
 * under 35°, none of them edges of the part. 35° also keeps clear of the angles parts are
 * designed with (30° and 45° chamfers). The Studio draws the same mesh with the same angle.
 */
export const PREVIEW_CREASE_ANGLE_DEG = 35

/** A point shared by more faces than this keeps flat normals; it bounds the pairwise step. */
const MAX_FACES_PER_POINT = 2048

const EMPTY = -1

/**
 * @param positions nine floats per triangle (three corners, xyz), not indexed
 * @param creaseAngleDeg faces further apart than this do not share a normal
 * @returns one unit normal per corner, laid out like `positions`
 */
export function computeCreaseNormals(positions: Float32Array, creaseAngleDeg: number): Float32Array {
    const cornerCount = Math.floor(positions.length / 9) * 3
    const faceCount = cornerCount / 3
    const normals = new Float32Array(positions.length)
    if (faceCount === 0) return normals

    // Per face, the unit normal (the crease test). Per corner, the face's vote there: twice its
    // area times the angle it spans at that corner.
    const unit = new Float32Array(faceCount * 3)
    const vote = new Float32Array(cornerCount)
    for (let f = 0; f < faceCount; f++) {
        const p = f * 9
        const ax = positions[p + 3] - positions[p], ay = positions[p + 4] - positions[p + 1], az = positions[p + 5] - positions[p + 2]
        const bx = positions[p + 6] - positions[p], by = positions[p + 7] - positions[p + 1], bz = positions[p + 8] - positions[p + 2]
        const nx = ay * bz - az * by, ny = az * bx - ax * bz, nz = ax * by - ay * bx
        const doubleArea = Math.hypot(nx, ny, nz)
        // A zero-area triangle has no direction: it neither votes nor is drawn.
        if (!(doubleArea > 0) || !Number.isFinite(doubleArea)) continue
        const o = f * 3
        unit[o] = nx / doubleArea; unit[o + 1] = ny / doubleArea; unit[o + 2] = nz / doubleArea
        // With a = B - A and b = C - A: the angle at A is between a and b, at B between -a and
        // b - a, at C between -b and a - b. Every pair has the same cross product length.
        const aa = ax * ax + ay * ay + az * az, bb = bx * bx + by * by + bz * bz, ab = ax * bx + ay * by + az * bz
        vote[f * 3] = Math.atan2(doubleArea, ab) * doubleArea
        vote[f * 3 + 1] = Math.atan2(doubleArea, aa - ab) * doubleArea
        vote[f * 3 + 2] = Math.atan2(doubleArea, bb - ab) * doubleArea
    }

    // Corners at the same point become one vertex. Equality is exact: the exporters and the
    // decoder write a shared point with identical bits, and a tolerance would also join the two
    // walls of a thin slot.
    let tableSize = 16
    while (tableSize < cornerCount * 2) tableSize *= 2
    const mask = tableSize - 1
    const table = new Int32Array(tableSize).fill(EMPTY)
    const vertexOfCorner = new Int32Array(cornerCount)
    const firstCorner = new Int32Array(cornerCount)
    let vertexCount = 0
    const bits = new Int32Array(positions.buffer, positions.byteOffset, cornerCount * 3)
    for (let c = 0; c < cornerCount; c++) {
        const p = c * 3
        const x = positions[p], y = positions[p + 1], z = positions[p + 2]
        // Hash the bit patterns; -0 equals 0, so it must hash like 0 too.
        let slot = (Math.imul(x === 0 ? 0 : bits[p], 0x9e3779b1)
            ^ Math.imul(y === 0 ? 0 : bits[p + 1], 0x85ebca6b)
            ^ Math.imul(z === 0 ? 0 : bits[p + 2], 0xc2b2ae35))
        slot = (slot ^ (slot >>> 15)) & mask
        for (;;) {
            const vertex = table[slot]
            if (vertex === EMPTY) {
                table[slot] = vertexCount
                firstCorner[vertexCount] = c
                vertexOfCorner[c] = vertexCount++
                break
            }
            const q = firstCorner[vertex] * 3
            if (positions[q] === x && positions[q + 1] === y && positions[q + 2] === z) {
                vertexOfCorner[c] = vertex
                break
            }
            slot = (slot + 1) & mask
        }
    }

    // The corners around each vertex, as one flat list with an offset per vertex.
    const start = new Int32Array(vertexCount + 1)
    for (let c = 0; c < cornerCount; c++) start[vertexOfCorner[c] + 1]++
    for (let v = 0; v < vertexCount; v++) start[v + 1] += start[v]
    const cursor = start.slice(0, vertexCount)
    const cornersAround = new Int32Array(cornerCount)
    for (let c = 0; c < cornerCount; c++) cornersAround[cursor[vertexOfCorner[c]]++] = c

    const creaseCos = Math.cos((Math.min(Math.max(creaseAngleDeg, 0), 180) * Math.PI) / 180)
    for (let c = 0; c < cornerCount; c++) {
        const own = ((c / 3) | 0) * 3
        const ux = unit[own], uy = unit[own + 1], uz = unit[own + 2]
        const vertex = vertexOfCorner[c]
        const from = start[vertex], to = start[vertex + 1]
        let nx = 0, ny = 0, nz = 0
        if (to - from <= MAX_FACES_PER_POINT) {
            for (let i = from; i < to; i++) {
                const corner = cornersAround[i]
                const other = ((corner / 3) | 0) * 3
                const ox = unit[other], oy = unit[other + 1], oz = unit[other + 2]
                if (ux * ox + uy * oy + uz * oz >= creaseCos) {
                    const weight = vote[corner]
                    nx += ox * weight; ny += oy * weight; nz += oz * weight
                }
            }
        }
        let length = Math.hypot(nx, ny, nz)
        if (!(length > 0)) { nx = ux; ny = uy; nz = uz; length = Math.hypot(nx, ny, nz) }
        const o = c * 3
        if (length > 0) {
            normals[o] = nx / length; normals[o + 1] = ny / length; normals[o + 2] = nz / length
        } else {
            // Degenerate triangle: any unit vector keeps the shader out of NaN.
            normals[o + 2] = 1
        }
    }
    return normals
}
