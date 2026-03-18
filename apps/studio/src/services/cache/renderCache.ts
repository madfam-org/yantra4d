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

interface CacheEntry {
  parts: SerializedPart[]
  timestamp: number
}

interface SerializedPart {
  type: string
  arrayBuffer: ArrayBuffer
  isGlb: boolean
  /** ArrayBuffer for the download-format file (e.g. STL) when it differs from the viewer blob. */
  downloadArrayBuffer?: ArrayBuffer
}

interface CachedPart {
  type: string
  blob: Blob
  /** Blob for the download-format file, if stored separately from the viewer blob. */
  downloadBlob?: Blob
}

const DB_NAME = 'yantra4d-render-cache'
const DB_VERSION = 1
const STORE_NAME = 'renders'
const TTL_MS = 24 * 60 * 60 * 1000
const MAX_ENTRIES = 500

let dbPromise: Promise<IDBDatabase> | null = null

function openDB(): Promise<IDBDatabase> {
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

async function hashKey(obj: Record<string, unknown>): Promise<string> {
  const raw = JSON.stringify(obj, Object.keys(obj).sort())
  const buf = new TextEncoder().encode(raw)
  const hash = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('')
}

/**
 * Build a cache key object from render parameters.
 */
export async function makeCacheKey(
  project: string,
  mode: string,
  params: Record<string, unknown>,
  format: string = 'stl'
): Promise<string> {
  return hashKey({ project, mode, ...params, format })
}

/**
 * Retrieve cached render parts from IndexedDB.
 * Returns null on miss, expired, or any error.
 */
export async function get(key: string): Promise<CachedPart[] | null> {
  try {
    const db = await openDB()
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const entry = await new Promise<CacheEntry | undefined>((resolve, reject) => {
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
    return entry.parts.map(p => {
      const part: CachedPart = {
        type: p.type,
        blob: new Blob([p.arrayBuffer], { type: p.isGlb ? 'model/gltf-binary' : 'model/stl' }),
      }
      if (p.downloadArrayBuffer) {
        part.downloadBlob = new Blob([p.downloadArrayBuffer], { type: 'model/stl' })
      }
      return part
    })
  } catch {
    return null
  }
}

interface PutPart {
  type: string
  url?: string
  blob?: Blob
  download_url?: string
}

/**
 * Store render parts in IndexedDB.
 * Accepts either blob URLs (fetched) or Blobs directly (WASM path).
 */
export async function put(key: string, parts: PutPart[]): Promise<void> {
  try {
    const serialized = await Promise.all(
      parts.map(async (p) => {
        let arrayBuffer: ArrayBuffer
        if (p.blob) {
          arrayBuffer = await p.blob.arrayBuffer()
        } else if (p.url) {
          const res = await fetch(p.url)
          arrayBuffer = await res.arrayBuffer()
        } else {
          return null
        }
        const urlPath = (p.url || '').split('?')[0].toLowerCase()
        const result: SerializedPart = { type: p.type, arrayBuffer, isGlb: urlPath.endsWith('.glb') }

        // Also store the download-format blob (e.g. STL) when it differs from
        // the viewer URL. This ensures download_url survives L2 cache round-trips
        // so handleDownloadStl can skip redundant re-renders.
        if (p.download_url && p.download_url !== p.url) {
          try {
            const dlRes = await fetch(p.download_url)
            result.downloadArrayBuffer = await dlRes.arrayBuffer()
          } catch {
            // Non-fatal — download will fall back to re-render
          }
        }
        return result
      })
    )

    const validParts = serialized.filter((p): p is SerializedPart => p !== null)
    if (validParts.length === 0) return

    const db = await openDB()
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    store.put({ parts: validParts, timestamp: Date.now() }, key)
    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })

    // Evict if over limit
    evict().catch(() => {})
  } catch {
    // Cache write failure is non-fatal
  }
}

async function del(key: string): Promise<void> {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, 'readwrite')
  tx.objectStore(STORE_NAME).delete(key)
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

/**
 * Remove expired entries and LRU-evict if over MAX_ENTRIES.
 */
async function evict(): Promise<void> {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, 'readwrite')
  const store = tx.objectStore(STORE_NAME)
  const allKeys = await new Promise<IDBValidKey[]>((resolve, reject) => {
    const req = store.getAllKeys()
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })

  const entries: { key: IDBValidKey; timestamp: number }[] = []
  for (const key of allKeys) {
    const entry = await new Promise<CacheEntry | undefined>((resolve, reject) => {
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
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

/**
 * Clear the entire cache.
 */
export async function clear(): Promise<void> {
  try {
    const db = await openDB()
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).clear()
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch {
    // Non-fatal
  }
}
