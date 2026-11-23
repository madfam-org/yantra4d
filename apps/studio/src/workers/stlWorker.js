import { STLLoader } from 'three/examples/jsm/loaders/STLLoader'
import { computeCreaseNormals, RENDER_CREASE_ANGLE_DEG } from '../lib/creaseNormals'

self.onmessage = async (e) => {
    const { url, id, authHeader } = e.data
    try {
        // authHeader is set by useWorkerLoader for same-origin, access-gated
        // private-project artifacts; an unauthenticated GET returns 403.
        const response = await fetch(url, authHeader ? { headers: { Authorization: authHeader } } : undefined)
        if (!response.ok) {
            throw new Error(`Failed to fetch STL: HTTP ${response.status}`)
        }

        // We get the raw ArrayBuffer from the fetch
        const buffer = await response.arrayBuffer()

        // STLLoader's parse method accepts an ArrayBuffer or a String
        const loader = new STLLoader()
        const geometry = loader.parse(buffer)

        // We must copy the underlying array buffer because Transferable Objects
        // will detach it from the worker.
        const rawPositions = new Float32Array(geometry.getAttribute('position').array)

        // An STL carries one normal per facet, which draws every triangle as its own flat
        // patch. Crease-angle normals shade a round face as one surface and keep real edges
        // sharp; they are worked out here so the main thread never pays for it.
        const rawNormals = computeCreaseNormals(rawPositions, RENDER_CREASE_ANGLE_DEG)

        // Prepare transferables (zero-copy memory pass to main thread)
        const transferables = [rawPositions.buffer, rawNormals.buffer]

        self.postMessage(
            {
                id,
                success: true,
                geometryData: {
                    positions: rawPositions,
                    normals: rawNormals
                }
            },
            transferables
        )

    } catch (err) {
        self.postMessage({ id, success: false, error: err.message })
    }
}
