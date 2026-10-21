import type { BufferAttribute, BufferGeometry, InterleavedBufferAttribute } from 'three'

export interface AssemblyGeometry {
  type: string
  geometry: BufferGeometry
}

export const ASSEMBLY_CACHE_MAX_BYTES = 32 * 1024 * 1024
export const ASSEMBLY_CACHE_MAX_ENTRIES = 16

function backingBytes(parts: AssemblyGeometry[]): number {
  const buffers = new Set<ArrayBufferLike>()
  const add = (attribute: BufferAttribute | InterleavedBufferAttribute) => {
    buffers.add(attribute.array.buffer)
  }
  for (const { geometry } of parts) {
    Object.values(geometry.attributes).forEach(add)
    if (geometry.index) add(geometry.index)
    Object.values(geometry.morphAttributes).forEach(attributes => attributes.forEach(add))
  }
  return [...buffers].reduce((total, buffer) => total + buffer.byteLength, 0)
}

/** Borrowed CPU source geometry only. Grid cells own the rendered clones. */
export class AssemblyGeometryCache {
  private entries = new Map<string, { parts: AssemblyGeometry[]; bytes: number }>()
  private retainedBytes = 0

  constructor(
    private maxBytes = ASSEMBLY_CACHE_MAX_BYTES,
    private maxEntries = ASSEMBLY_CACHE_MAX_ENTRIES,
  ) {}

  get(key: string): AssemblyGeometry[] | undefined {
    const entry = this.entries.get(key)
    if (!entry) return undefined
    this.entries.delete(key)
    this.entries.set(key, entry)
    return entry.parts
  }

  set(key: string, parts: AssemblyGeometry[]): void {
    this.delete(key)
    const bytes = backingBytes(parts)
    if (bytes > this.maxBytes || this.maxEntries < 1) return
    this.entries.set(key, { parts, bytes })
    this.retainedBytes += bytes
    while (this.retainedBytes > this.maxBytes || this.entries.size > this.maxEntries) {
      this.delete(this.entries.keys().next().value!)
    }
  }

  private delete(key: string): void {
    const entry = this.entries.get(key)
    if (entry) this.retainedBytes -= entry.bytes
    // Dropping the cache reference releases retention. Do not mutate the CPU
    // arrays: an active grid may still use this source to create its own clones.
    this.entries.delete(key)
  }

  get size(): number { return this.entries.size }
  get bytes(): number { return this.retainedBytes }
}
