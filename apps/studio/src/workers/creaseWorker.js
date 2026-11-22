import { computeCreaseNormals } from '../lib/creaseNormals'

// Crease-angle normals for one triangle soup, off the main thread. Every real render reaches
// the viewer as a GLB without normals, so this runs once per loaded mesh.
self.onmessage = (event) => {
    const { id, positions, creaseAngleDeg } = event.data
    try {
        const normals = computeCreaseNormals(positions, creaseAngleDeg)
        self.postMessage({ id, normals }, [normals.buffer])
    } catch (error) {
        self.postMessage({ id, error: String(error?.message || error) })
    }
}
