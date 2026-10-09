/**
 * Feature-edge extraction off the main thread.
 *
 * Runs three's own EdgesGeometry on a copy of the mesh positions/index, so the
 * segments are identical to computing them in place — but a 100k-triangle
 * model no longer blocks the main thread for most of a second.
 */
import { BufferAttribute, BufferGeometry, EdgesGeometry } from 'three'

self.onmessage = (event) => {
  const { id, positions, index, threshold } = event.data
  try {
    const geometry = new BufferGeometry()
    geometry.setAttribute('position', new BufferAttribute(positions, 3))
    if (index) geometry.setIndex(new BufferAttribute(index, 1))
    const edges = new EdgesGeometry(geometry, threshold).attributes.position.array
    self.postMessage({ id, edges }, [edges.buffer])
  } catch (error) {
    self.postMessage({ id, error: String(error?.message || error) })
  }
}
