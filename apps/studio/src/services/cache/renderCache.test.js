import { describe, it, expect, vi, beforeEach } from 'vitest'

// ---------------------------------------------------------------------------
// IndexedDB mock
//
// The real IDB fires transaction.oncomplete after all store operations.
// We track store writes and fire oncomplete from store.put/clear so the
// awaiting code in renderCache.js resolves correctly.
// ---------------------------------------------------------------------------
let storeData
let activeTx

function fireOncomplete() {
  if (activeTx && !activeTx._fired) {
    activeTx._fired = true
    const tx = activeTx
    Promise.resolve().then(() => tx.oncomplete?.())
  }
}

function createMockObjectStore() {
  return {
    get(key) {
      const req = { result: storeData[key] ?? undefined }
      Promise.resolve().then(() => req.onsuccess?.())
      return req
    },
    put(value, key) {
      storeData[key] = value
      const req = {}
      Promise.resolve().then(() => req.onsuccess?.())
      fireOncomplete()
      return req
    },
    delete(key) {
      delete storeData[key]
      const req = {}
      Promise.resolve().then(() => req.onsuccess?.())
      return req
    },
    clear() {
      for (const k of Object.keys(storeData)) delete storeData[k]
      const req = {}
      Promise.resolve().then(() => req.onsuccess?.())
      fireOncomplete()
      return req
    },
    getAllKeys() {
      const req = { result: Object.keys(storeData) }
      Promise.resolve().then(() => req.onsuccess?.())
      return req
    },
  }
}

function createMockIndexedDB() {
  const mockStore = createMockObjectStore()
  const mockDB = {
    objectStoreNames: { contains: () => true },
    createObjectStore: vi.fn(),
    transaction() {
      const tx = {
        objectStore: () => mockStore,
        oncomplete: null,
        onerror: null,
        error: null,
        _fired: false,
      }
      activeTx = tx
      // Fallback: fire oncomplete after several microticks for read-only txs
      Promise.resolve()
        .then(() => Promise.resolve())
        .then(() => Promise.resolve())
        .then(() => Promise.resolve())
        .then(() => {
          if (!tx._fired) {
            tx._fired = true
            tx.oncomplete?.()
          }
        })
      return tx
    },
  }
  return {
    open() {
      const req = { result: mockDB }
      Promise.resolve().then(() => {
        req.onupgradeneeded?.()
        req.onsuccess?.()
      })
      return req
    },
  }
}

function createFailingIndexedDB() {
  return {
    open() {
      const req = { error: new Error('DB error') }
      Promise.resolve().then(() => req.onerror?.())
      return req
    },
  }
}

// ---------------------------------------------------------------------------
// crypto.subtle mock
// ---------------------------------------------------------------------------
function createMockCrypto() {
  return {
    subtle: {
      async digest(_algo, buffer) {
        const bytes = new Uint8Array(buffer)
        let sum = 0
        for (const b of bytes) sum = (sum + b) % 256
        const out = new Uint8Array(32)
        for (let i = 0; i < 32; i++) out[i] = (sum + i) % 256
        return out.buffer
      },
    },
    getRandomValues: (arr) => arr,
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('renderCache', () => {
  beforeEach(() => {
    storeData = {}
    activeTx = null
    vi.stubGlobal('indexedDB', createMockIndexedDB())
    vi.stubGlobal('crypto', createMockCrypto())
    vi.resetModules()
  })

  async function loadModule() {
    return import('./renderCache.js')
  }

  // ---------- makeCacheKey ----------

  describe('makeCacheKey', () => {
    it('returns a 64-char hex string', async () => {
      const { makeCacheKey } = await loadModule()
      const key = await makeCacheKey('my-project', 'full', { height: 10 })
      expect(typeof key).toBe('string')
      expect(key).toMatch(/^[0-9a-f]{64}$/)
    })

    it('produces different keys for different inputs', async () => {
      const { makeCacheKey } = await loadModule()
      const a = await makeCacheKey('proj', 'full', { h: 1 })
      const b = await makeCacheKey('proj', 'full', { h: 2 })
      expect(a).not.toBe(b)
    })

    it('includes format in key computation', async () => {
      const { makeCacheKey } = await loadModule()
      const a = await makeCacheKey('p', 'm', {}, 'stl')
      const b = await makeCacheKey('p', 'm', {}, '3mf')
      expect(a).not.toBe(b)
    })

    it('defaults format to stl', async () => {
      const { makeCacheKey } = await loadModule()
      const a = await makeCacheKey('p', 'm', {})
      const b = await makeCacheKey('p', 'm', {}, 'stl')
      expect(a).toBe(b)
    })
  })

  // ---------- get ----------

  describe('get', () => {
    it('returns null on cache miss', async () => {
      const { get } = await loadModule()
      const result = await get('nonexistent-key')
      expect(result).toBeNull()
    })

    it('returns parts array on cache hit', async () => {
      const buf = new ArrayBuffer(4)
      storeData['hit-key'] = {
        parts: [{ type: 'shell', arrayBuffer: buf, isGlb: false }],
        timestamp: Date.now(),
      }
      const { get } = await loadModule()
      const result = await get('hit-key')
      expect(result).not.toBeNull()
      expect(result).toHaveLength(1)
      expect(result[0].type).toBe('shell')
      expect(result[0].blob).toBeInstanceOf(Blob)
    })

    it('sets gltf-binary blob type for GLB entries', async () => {
      const buf = new ArrayBuffer(4)
      storeData['glb-key'] = {
        parts: [{ type: 'shell', arrayBuffer: buf, isGlb: true }],
        timestamp: Date.now(),
      }
      const { get } = await loadModule()
      const result = await get('glb-key')
      expect(result[0].blob.type).toBe('model/gltf-binary')
    })

    it('sets model/stl blob type for non-GLB entries', async () => {
      const buf = new ArrayBuffer(4)
      storeData['stl-key'] = {
        parts: [{ type: 'shell', arrayBuffer: buf, isGlb: false }],
        timestamp: Date.now(),
      }
      const { get } = await loadModule()
      const result = await get('stl-key')
      expect(result[0].blob.type).toBe('model/stl')
    })

    it('returns null for expired entries', async () => {
      storeData['old-key'] = {
        parts: [{ type: 'shell', arrayBuffer: new ArrayBuffer(4) }],
        timestamp: Date.now() - 25 * 60 * 60 * 1000,
      }
      const { get } = await loadModule()
      const result = await get('old-key')
      expect(result).toBeNull()
    })

    it('returns null when DB open fails', async () => {
      vi.stubGlobal('indexedDB', createFailingIndexedDB())
      vi.resetModules()
      const { get } = await import('./renderCache.js')
      const result = await get('any-key')
      expect(result).toBeNull()
    })
  })

  // ---------- put ----------

  describe('put', () => {
    it('stores parts from URLs via fetch', async () => {
      const buf = new ArrayBuffer(8)
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        arrayBuffer: () => Promise.resolve(buf),
      }))
      const { put } = await loadModule()
      await put('url-key', [{ type: 'base', url: 'http://example.com/model.stl' }])
      expect(storeData['url-key']).toBeDefined()
      expect(storeData['url-key'].parts).toHaveLength(1)
      expect(storeData['url-key'].parts[0].type).toBe('base')
      expect(storeData['url-key'].parts[0].isGlb).toBe(false)
      expect(storeData['url-key'].timestamp).toBeGreaterThan(0)
    })

    it('marks GLB URLs with isGlb flag', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
      }))
      const { put } = await loadModule()
      await put('glb-key', [{ type: 'base', url: 'http://example.com/model.glb' }])
      expect(storeData['glb-key'].parts[0].isGlb).toBe(true)
    })

    it('marks GLB URLs with query string cache-buster as isGlb', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
      }))
      const { put } = await loadModule()
      await put('glb-qs-key', [{ type: 'base', url: 'http://example.com/model.glb?t=1708611200000' }])
      expect(storeData['glb-qs-key'].parts[0].isGlb).toBe(true)
    })

    it('does not throw when storing blobs', async () => {
      const { put } = await loadModule()
      const blob = new Blob(['data'], { type: 'model/stl' })
      // put() catches all errors internally, so it should always resolve
      await expect(put('blob-key', [{ type: 'shell', blob }])).resolves.toBeUndefined()
    })

    it('round-trips via put then get for URL parts', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(16)),
      }))
      const { put, get } = await loadModule()
      await put('rt-key', [{ type: 'shell', url: 'http://example.com/model.stl' }])
      const result = await get('rt-key')
      expect(result).not.toBeNull()
      expect(result).toHaveLength(1)
      expect(result[0].type).toBe('shell')
      expect(result[0].blob).toBeInstanceOf(Blob)
    })

    it('skips parts with neither blob nor url', async () => {
      const { put } = await loadModule()
      await put('empty-key', [{ type: 'shell' }])
      expect(storeData['empty-key']).toBeUndefined()
    })

    it('filters out invalid parts from mixed input', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
      }))
      const { put } = await loadModule()
      await put('mixed-key', [
        { type: 'shell', url: 'http://example.com/part.stl' },
        { type: 'invalid' },
      ])
      expect(storeData['mixed-key'].parts).toHaveLength(1)
    })

    it('does not throw when DB open fails', async () => {
      vi.stubGlobal('indexedDB', createFailingIndexedDB())
      vi.resetModules()
      const { put } = await import('./renderCache.js')
      const blob = new Blob(['data'])
      await expect(put('k', [{ type: 'x', blob }])).resolves.toBeUndefined()
    })
  })

  // ---------- eviction (triggered by put) ----------

  describe('eviction', () => {
    it('evicts expired entries during put', async () => {
      // Pre-seed an expired entry
      storeData['expired-1'] = {
        parts: [{ type: 'shell', arrayBuffer: new ArrayBuffer(4) }],
        timestamp: Date.now() - 25 * 60 * 60 * 1000, // 25h ago
      }
      storeData['fresh-1'] = {
        parts: [{ type: 'shell', arrayBuffer: new ArrayBuffer(4) }],
        timestamp: Date.now(),
      }

      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
      }))
      const { put } = await loadModule()
      await put('new-key', [{ type: 'shell', url: 'http://example.com/m.stl' }])

      // The expired entry should be deleted during eviction
      // (eviction happens asynchronously after put, give microtasks time)
      await new Promise(r => setTimeout(r, 50))
      expect(storeData['expired-1']).toBeUndefined()
      expect(storeData['fresh-1']).toBeDefined()
    })
  })

  // ---------- onupgradeneeded (store creation) ----------

  describe('DB upgrade', () => {
    it('creates object store when it does not exist', async () => {
      const createFn = vi.fn()
      const mockStore = createMockObjectStore()
      const mockDB = {
        objectStoreNames: { contains: () => false },
        createObjectStore: createFn,
        transaction() {
          const tx = {
            objectStore: () => mockStore,
            oncomplete: null,
            onerror: null,
            error: null,
            _fired: false,
          }
          activeTx = tx
          Promise.resolve()
            .then(() => Promise.resolve())
            .then(() => Promise.resolve())
            .then(() => Promise.resolve())
            .then(() => {
              if (!tx._fired) {
                tx._fired = true
                tx.oncomplete?.()
              }
            })
          return tx
        },
      }
      vi.stubGlobal('indexedDB', {
        open() {
          const req = { result: mockDB }
          Promise.resolve().then(() => {
            req.onupgradeneeded?.()
            req.onsuccess?.()
          })
          return req
        },
      })
      vi.resetModules()

      const { get } = await import('./renderCache.js')
      await get('any-key')
      expect(createFn).toHaveBeenCalledWith('renders')
    })
  })

  // ---------- clear ----------

  describe('clear', () => {
    it('clears all entries', async () => {
      storeData['a'] = { parts: [], timestamp: Date.now() }
      storeData['b'] = { parts: [], timestamp: Date.now() }
      const { clear } = await loadModule()
      await clear()
      expect(Object.keys(storeData)).toHaveLength(0)
    })

    it('does not throw when DB open fails', async () => {
      vi.stubGlobal('indexedDB', createFailingIndexedDB())
      vi.resetModules()
      const { clear } = await import('./renderCache.js')
      await expect(clear()).resolves.toBeUndefined()
    })
  })
})
