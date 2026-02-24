/**
 * IndexedDB-backed persistent render cache.
 *
 * DB:    "yantra4d-render-cache", version 1
 * Store: "renders"
 * Key:   SHA-256 hex of JSON.stringify({ project, mode, ...sorted_params, format })
 * Value: { parts: [{ type, arrayBuffer }], timestamp }
 * TTL:   24 hours
 * Max:   500 entries (LRU eviction by timestamp)
 */

const DB_NAME = 'yantra4d-render-cache'
const DB_VERSION = 1
const STORE_NAME = 'renders'
const TTL_MS = 24 * 60 * 60 * 1000
const MAX_ENTRIES = 500

let dbPromise = null

function openDB() {
  if (dbPromise) return dbPromise
  dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME)
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
  return dbPromise
}

async function hashKey(obj) {
  const raw = JSON.stringify(obj, Object.keys(obj).sort())
  const buf = new TextEncoder().encode(raw)
  const hash = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('')
}

/**
 * Build a cache key object from render parameters.
 * @param {string} project - Project slug
 * @param {string} mode - Render mode
 * @param {object} params - Render parameters (already filtered by manifest)
 * @param {string} format - Export format (stl, 3mf, etc.)
 * @returns {Promise<string>} SHA-256 hex key
 */
export async function makeCacheKey(project, mode, params, format = 'stl') {
  return hashKey({ project, mode, ...params, format })
}

/**
 * Retrieve cached render parts from IndexedDB.
 * Returns null on miss, expired, or any error.
 * @param {string} key - SHA-256 cache key
 * @returns {Promise<Array|null>} Array of { type, blob } or null
 */
export async function get(key) {
  try {
    const db = await openDB()
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const entry = await new Promise((resolve, reject) => {
      const req = store.get(key)
      req.onsuccess = () => resolve(req.result)
      req.onerror = () => reject(req.error)
    })

    if (!entry) return null
    if (Date.now() - entry.timestamp > TTL_MS) {
      // Expired — don't block on deletion
      del(key).catch(() => {})
      return null
    }

    // Convert stored ArrayBuffers back to Blobs
    return entry.parts.map(p => ({
      type: p.type,
      blob: new Blob([p.arrayBuffer], { type: p.isGlb ? 'model/gltf-binary' : 'model/stl' })
    }))
  } catch {
    return null
  }
}

/**
 * Store render parts in IndexedDB.
 * Accepts either blob URLs (fetched) or Blobs directly (WASM path).
 * @param {string} key - SHA-256 cache key
 * @param {Array<{type: string, url?: string, blob?: Blob}>} parts
 */
export async function put(key, parts) {
  try {
    const serialized = await Promise.all(
      parts.map(async (p) => {
        let arrayBuffer
        if (p.blob) {
          arrayBuffer = await p.blob.arrayBuffer()
        } else if (p.url) {
          const res = await fetch(p.url)
          arrayBuffer = await res.arrayBuffer()
        } else {
          return null
        }
        return { type: p.type, arrayBuffer, isGlb: p.url?.endsWith('.glb') || false }
      })
    )

    const validParts = serialized.filter(Boolean)
    if (validParts.length === 0) return

    const db = await openDB()
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    store.put({ parts: validParts, timestamp: Date.now() }, key)
    await new Promise((resolve, reject) => {
      tx.oncomplete = resolve
      tx.onerror = () => reject(tx.error)
    })

    // Evict if over limit
    evict().catch(() => {})
  } catch {
    // Cache write failure is non-fatal
  }
}

async function del(key) {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, 'readwrite')
  tx.objectStore(STORE_NAME).delete(key)
  return new Promise((resolve, reject) => {
    tx.oncomplete = resolve
    tx.onerror = () => reject(tx.error)
  })
}

/**
 * Remove expired entries and LRU-evict if over MAX_ENTRIES.
 */
async function evict() {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, 'readwrite')
  const store = tx.objectStore(STORE_NAME)
  const allKeys = await new Promise((resolve, reject) => {
    const req = store.getAllKeys()
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })

  const entries = []
  for (const key of allKeys) {
    const entry = await new Promise((resolve, reject) => {
      const req = store.get(key)
      req.onsuccess = () => resolve(req.result)
      req.onerror = () => reject(req.error)
    })
    if (!entry) continue
    if (Date.now() - entry.timestamp > TTL_MS) {
      store.delete(key)
    } else {
      entries.push({ key, timestamp: entry.timestamp })
    }
  }

  // LRU eviction: sort by timestamp ascending, remove oldest
  if (entries.length > MAX_ENTRIES) {
    entries.sort((a, b) => a.timestamp - b.timestamp)
    const toRemove = entries.slice(0, entries.length - MAX_ENTRIES)
    for (const e of toRemove) {
      store.delete(e.key)
    }
  }

  return new Promise((resolve, reject) => {
    tx.oncomplete = resolve
    tx.onerror = () => reject(tx.error)
  })
}

/**
 * Clear the entire cache.
 */
export async function clear() {
  try {
    const db = await openDB()
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).clear()
    return new Promise((resolve, reject) => {
      tx.oncomplete = resolve
      tx.onerror = () => reject(tx.error)
    })
  } catch {
    // Non-fatal
  }
}
