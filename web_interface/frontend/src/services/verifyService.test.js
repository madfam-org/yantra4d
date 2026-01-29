import { describe, it, expect } from 'vitest'
import { parseSTL, getBoundingBox } from '../lib/stl-utils'

/**
 * Build a minimal binary STL with one triangle.
 * Vertices: (0,0,0), (1,0,0), (0,1,0)
 */
function makeOneTriangleSTL() {
  // 80 header + 4 faceCount + 1*(12 normal + 36 verts + 2 attr) = 134 bytes
  const buf = new ArrayBuffer(84 + 50)
  const view = new DataView(buf)
  view.setUint32(80, 1, true) // 1 face

  let offset = 84
  // Normal (0,0,1)
  view.setFloat32(offset, 0, true); offset += 4
  view.setFloat32(offset, 0, true); offset += 4
  view.setFloat32(offset, 1, true); offset += 4
  // Vertex 0: (0,0,0)
  view.setFloat32(offset, 0, true); offset += 4
  view.setFloat32(offset, 0, true); offset += 4
  view.setFloat32(offset, 0, true); offset += 4
  // Vertex 1: (1,0,0)
  view.setFloat32(offset, 1, true); offset += 4
  view.setFloat32(offset, 0, true); offset += 4
  view.setFloat32(offset, 0, true); offset += 4
  // Vertex 2: (0,1,0)
  view.setFloat32(offset, 0, true); offset += 4
  view.setFloat32(offset, 1, true); offset += 4
  view.setFloat32(offset, 0, true); offset += 4
  // Attribute byte count
  view.setUint16(offset, 0, true)

  return buf
}

describe('parseSTL', () => {
  it('parses a 1-triangle STL correctly', () => {
    const result = parseSTL(makeOneTriangleSTL())
    expect(result.faceCount).toBe(1)
    expect(result.vertices.length).toBe(9) // 1 face * 3 verts * 3 coords
    expect(result.faces.length).toBe(3)
    // Vertex 1 should be (1,0,0)
    expect(result.vertices[3]).toBe(1)
    expect(result.vertices[4]).toBe(0)
    expect(result.vertices[5]).toBe(0)
  })
})

describe('getBoundingBox', () => {
  it('computes correct min/max/size from known vertices', () => {
    const verts = new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0])
    const bbox = getBoundingBox(verts)
    expect(bbox.min).toEqual([0, 0, 0])
    expect(bbox.max).toEqual([1, 1, 0])
    expect(bbox.size).toEqual([1, 1, 0])
  })

  it('handles empty array', () => {
    const bbox = getBoundingBox(new Float32Array([]))
    expect(bbox.min).toEqual([Infinity, Infinity, Infinity])
    expect(bbox.max).toEqual([-Infinity, -Infinity, -Infinity])
  })
})
