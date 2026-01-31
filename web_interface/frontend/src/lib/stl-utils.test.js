import { describe, it, expect } from 'vitest'
import { parseSTL, getBoundingBox } from './stl-utils'

function makeSTLBuffer(faceCount) {
  const size = 84 + faceCount * 50
  const buf = new ArrayBuffer(size)
  const view = new DataView(buf)
  view.setUint32(80, faceCount, true)
  // Write one triangle at origin for face 0
  if (faceCount > 0) {
    let offset = 84 + 12 // skip normal
    const coords = [0, 0, 0, 1, 0, 0, 0, 1, 0]
    for (const c of coords) {
      view.setFloat32(offset, c, true)
      offset += 4
    }
  }
  return buf
}

describe('parseSTL', () => {
  it('parses valid single-face STL', () => {
    const buf = makeSTLBuffer(1)
    const result = parseSTL(buf)
    expect(result.faceCount).toBe(1)
    expect(result.vertices).toBeInstanceOf(Float32Array)
    expect(result.vertices.length).toBe(9)
    expect(result.faces).toBeInstanceOf(Uint32Array)
    expect(result.faces.length).toBe(3)
  })

  it('throws on too-small buffer', () => {
    const buf = new ArrayBuffer(10)
    expect(() => parseSTL(buf)).toThrow('buffer too small')
  })

  it('throws on face count overflow', () => {
    const buf = new ArrayBuffer(84)
    const view = new DataView(buf)
    view.setUint32(80, 20_000_000, true)
    expect(() => parseSTL(buf)).toThrow('face count exceeds')
  })

  it('throws on truncated buffer', () => {
    const buf = new ArrayBuffer(84 + 10) // needs 84 + 50 for 1 face
    const view = new DataView(buf)
    view.setUint32(80, 1, true)
    expect(() => parseSTL(buf)).toThrow('buffer smaller than expected')
  })
})

describe('getBoundingBox', () => {
  it('computes bounding box for known vertices', () => {
    const verts = new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0])
    const bb = getBoundingBox(verts)
    expect(bb.min).toEqual([0, 0, 0])
    expect(bb.max).toEqual([1, 1, 0])
    expect(bb.size).toEqual([1, 1, 0])
  })
})
