import { describe, it, expect } from 'vitest'
import { BufferGeometry, BufferAttribute, InterleavedBuffer, InterleavedBufferAttribute } from 'three'
import { AssemblyGeometryCache } from './assemblyGeometryCache'

function part(buffer = new ArrayBuffer(36)) {
  return {type: 'body', geometry: new BufferGeometry().setAttribute('position', new BufferAttribute(new Float32Array(buffer, 0, 9), 3))}
}

describe('assembly CPU retention budget', () => {
  it('keeps a thousand distinct assemblies within both budgets', () => {
    const cache = new AssemblyGeometryCache(100, 2)
    const first = [part()]
    cache.set('first', first)
    for (let index = 0; index < 1000; index++) {
      cache.set(String(index), [part()])
      expect(cache.bytes).toBeLessThanOrEqual(100)
      expect(cache.size).toBeLessThanOrEqual(2)
    }
    expect(cache.get('first')).toBeUndefined()
    expect(cache.get('999')).toHaveLength(1)
    expect(first[0].geometry.clone().getAttribute('position').count).toBe(3)
  })

  it('accounts for whole backing buffers once across parts and attributes', () => {
    const cache = new AssemblyGeometryCache(128, 16)
    const buffer = new ArrayBuffer(128)
    const a = part(buffer)
    const b = part(buffer)
    a.geometry.setAttribute('normal', new BufferAttribute(new Float32Array(buffer, 36, 9), 3))
    b.geometry.setAttribute('uv', new InterleavedBufferAttribute(new InterleavedBuffer(new Float32Array(buffer), 2), 2, 0))
    cache.set('shared', [a, b])
    expect(cache.bytes).toBe(128)
    cache.set('new', [part()])
    expect(cache.get('shared')).toBeUndefined()
    expect(cache.bytes).toBe(36)
  })

  it('does not retain an oversized assembly or stale bytes after replacement', () => {
    const cache = new AssemblyGeometryCache(100, 16)
    cache.set('same', [part()])
    cache.set('same', [part(new ArrayBuffer(128))])
    expect(cache.get('same')).toBeUndefined()
    expect(cache.size).toBe(0)
    expect(cache.bytes).toBe(0)
  })
})
