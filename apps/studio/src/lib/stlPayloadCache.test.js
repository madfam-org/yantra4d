import { describe, it, expect } from 'vitest'
import { STLPayloadCache, STL_CACHE_MAX_BYTES, STL_CACHE_MAX_ENTRIES } from './stlPayloadCache'

const payload = (floats = 9) => ({ positions: new Float32Array(floats) })

describe('retained STL payload budget', () => {
  it('evicts least-recently-used entries and refreshes hits', () => {
    const cache = new STLPayloadCache(1000, 2)
    const a = payload()
    cache.set('a', a)
    cache.set('b', payload())
    expect(cache.get('a')).toBe(a)
    cache.set('c', payload())
    expect(cache.get('b')).toBeUndefined()
    expect(cache.get('a')).toBe(a)
    expect(cache.size).toBe(2)
  })

  it('enforces the byte budget independently of the entry limit', () => {
    const cache = new STLPayloadCache(72, 100)
    cache.set('a', payload())
    cache.set('b', payload())
    cache.set('c', payload())
    expect(cache.get('a')).toBeUndefined()
    expect(cache.bytes).toBe(72)
    expect(cache.size).toBe(2)
  })

  it('counts entire backing buffers and shared views only once', () => {
    const buffer = new ArrayBuffer(360)
    const item = { positions: new Float32Array(buffer, 0, 9), normals: new Float32Array(buffer, 36, 9) }
    const tooSmall = new STLPayloadCache(100)
    tooSmall.set('large', item)
    expect(tooSmall.size).toBe(0)
    const cache = new STLPayloadCache(360)
    cache.set('shared', item)
    expect(cache.bytes).toBe(360)
  })

  it('replaces accounting and refuses an oversized replacement', () => {
    const cache = new STLPayloadCache(72)
    cache.set('a', payload())
    cache.set('a', payload(18))
    expect(cache.bytes).toBe(72)
    cache.set('a', payload(27))
    expect(cache.size).toBe(0)
    expect(cache.bytes).toBe(0)
  })

  it('stays within the production budget across 1000 distinct models', () => {
    const cache = new STLPayloadCache()
    for (let i = 0; i < 1000; i++) {
      cache.set(String(i), payload(512 * 1024))
      expect(cache.bytes).toBeLessThanOrEqual(STL_CACHE_MAX_BYTES)
      expect(cache.size).toBeLessThanOrEqual(STL_CACHE_MAX_ENTRIES)
    }
    expect(cache.get('0')).toBeUndefined()
    expect(cache.get('999')).toBeDefined()
    expect(cache.bytes).toBe(STL_CACHE_MAX_BYTES)
  })
})
