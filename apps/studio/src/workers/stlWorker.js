import { STLLoader } from 'three/examples/jsm/loaders/STLLoader'

self.onmessage = async (e) => {
    const { url, id } = e.data
    try {
        const response = await fetch(url)
        if (!response.ok) {
            throw new Error(`Failed to fetch STL: HTTP ${response.status}`)
        }

        // We get the raw ArrayBuffer from the fetch
        const buffer = await response.arrayBuffer()

        // STLLoader's parse method accepts an ArrayBuffer or a String
        const loader = new STLLoader()
        const geometry = loader.parse(buffer)

        // Extract the raw interleaved arrays
        const positionAttr = geometry.getAttribute('position')
        const normalAttr = geometry.getAttribute('normal')

        // We must copy the underlying array buffers because Transferable Objects
        // will detach them from the worker.
        const rawPositions = new Float32Array(positionAttr.array)
        let rawNormals = null

        if (normalAttr) {
            rawNormals = new Float32Array(normalAttr.array)
        }

        // Prepare transferables (zero-copy memory pass to main thread)
        const transferables = [rawPositions.buffer]
        if (rawNormals) {
            transferables.push(rawNormals.buffer)
        }

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
