export interface STLPayload {
    positions: Float32Array
    normals?: Float32Array | null
}

export const STL_CACHE_MAX_BYTES = 32 * 1024 * 1024
export const STL_CACHE_MAX_ENTRIES = 16

/** CPU payloads only: mounted consumers own their mutable Three.js geometry. */
export class STLPayloadCache {
    private entries = new Map<string, { payload: STLPayload; bytes: number }>()
    private retainedBytes = 0

    constructor(
        private maxBytes = STL_CACHE_MAX_BYTES,
        private maxEntries = STL_CACHE_MAX_ENTRIES,
    ) {}

    get(key: string): STLPayload | undefined {
        const entry = this.entries.get(key)
        if (!entry) return undefined
        this.entries.delete(key)
        this.entries.set(key, entry)
        return entry.payload
    }

    set(key: string, payload: STLPayload): void {
        this.delete(key)
        // Count whole backing buffers: a small view can retain a large allocation.
        const buffers = new Set([payload.positions.buffer, payload.normals?.buffer])
        const bytes = [...buffers].reduce((total, buffer) => total + (buffer?.byteLength ?? 0), 0)
        if (bytes > this.maxBytes || this.maxEntries < 1) return
        this.entries.set(key, { payload, bytes })
        this.retainedBytes += bytes
        while (this.retainedBytes > this.maxBytes || this.entries.size > this.maxEntries) {
            this.delete(this.entries.keys().next().value!)
        }
    }

    private delete(key: string): void {
        const entry = this.entries.get(key)
        if (entry) this.retainedBytes -= entry.bytes
        this.entries.delete(key)
    }

    get size(): number { return this.entries.size }
    get bytes(): number { return this.retainedBytes }
}
