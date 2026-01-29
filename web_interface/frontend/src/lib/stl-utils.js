/**
 * Parse binary STL to get vertex/face data.
 * Returns { vertices: Float32Array, faces: Uint32Array, faceCount }
 */
export function parseSTL(buffer) {
  const view = new DataView(buffer)
  // Skip 80-byte header
  const faceCount = view.getUint32(80, true)
  const vertices = new Float32Array(faceCount * 9) // 3 verts * 3 coords
  const faces = new Uint32Array(faceCount * 3)

  let offset = 84
  for (let i = 0; i < faceCount; i++) {
    // Skip normal (12 bytes)
    offset += 12

    // Read 3 vertices (each 12 bytes = 3 floats)
    for (let v = 0; v < 3; v++) {
      const vi = i * 9 + v * 3
      vertices[vi] = view.getFloat32(offset, true); offset += 4
      vertices[vi + 1] = view.getFloat32(offset, true); offset += 4
      vertices[vi + 2] = view.getFloat32(offset, true); offset += 4
      faces[i * 3 + v] = i * 3 + v
    }

    // Skip attribute byte count
    offset += 2
  }

  return { vertices, faces, faceCount }
}

/**
 * Compute bounding box from vertices.
 */
export function getBoundingBox(vertices) {
  let minX = Infinity, minY = Infinity, minZ = Infinity
  let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity

  for (let i = 0; i < vertices.length; i += 3) {
    const x = vertices[i], y = vertices[i + 1], z = vertices[i + 2]
    if (x < minX) minX = x
    if (y < minY) minY = y
    if (z < minZ) minZ = z
    if (x > maxX) maxX = x
    if (y > maxY) maxY = y
    if (z > maxZ) maxZ = z
  }

  return {
    min: [minX, minY, minZ],
    max: [maxX, maxY, maxZ],
    size: [maxX - minX, maxY - minY, maxZ - minZ]
  }
}
