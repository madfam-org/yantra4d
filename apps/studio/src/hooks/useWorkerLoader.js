import React, { useState, useEffect, useMemo } from 'react'
import { BufferGeometry, BufferAttribute } from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'
import * as BufferGeometryUtils from 'three/examples/jsm/utils/BufferGeometryUtils'

// We create a singleton worker so we don't spin up dozens of threads.
// Notice the ?worker syntax which Vite requires to bundle it correctly.
let stlWorkerInstance = null

// Simple global cache so we don't re-parse geometries that haven't changed URLs
const geometryCache = new Map()

/**
 * A custom hook that drops-in alongside @react-three/fiber's useLoader,
 * but transparently routes .stl files to a background Web Worker.
 * If the file is a .gltf/.glb, it gracefully falls back to the synchronous GLTFLoader
 * so that we handle dual-formatting correctly during the architecture migration.
 */
export function useWorkerLoader(url, isGLTF = false) {
    // We use GLTFLoader.loadAsync instead of useLoader to avoid conditional hook violations
    const [gltfData, setGltfData] = useState(null)

    useEffect(() => {
        if (!isGLTF || !url) return
        const loader = new GLTFLoader()
        loader.loadAsync(url).then(data => setGltfData(data)).catch(console.error)
    }, [url, isGLTF])

    const [geometry, setGeometry] = useState(() => {
        // If it's a cached STL, return it immediately so we don't flicker.
        if (!isGLTF && url && geometryCache.has(url)) {
            return geometryCache.get(url)
        }
        return null
    })

    // GLTF parsing logic identical to the standard Viewer
    const gltfMergedGeom = useMemo(() => {
        if (!isGLTF || !gltfData) return null
        const geometries = []
        gltfData.scene.updateMatrixWorld(true)
        gltfData.scene.traverse((child) => {
            if (child.isMesh && child.geometry) {
                const clonedGeom = child.geometry.clone()
                clonedGeom.applyMatrix4(child.matrixWorld)
                geometries.push(clonedGeom)
            }
        })
        if (geometries.length === 0) return null
        if (geometries.length === 1) return geometries[0]
        return BufferGeometryUtils.mergeGeometries(geometries, false)
    }, [gltfData, isGLTF])


    // Worker execution logic 
    useEffect(() => {
        if (isGLTF || !url) return

        // Check cache first in case it just arrived
        if (geometryCache.has(url)) {
            // Delaying state update to avoid synchronous cascade render during effect
            Promise.resolve().then(() => setGeometry(geometryCache.get(url)))
            return
        }

        // Initialize singleton worker
        if (!stlWorkerInstance) {
            stlWorkerInstance = new Worker(new URL('../workers/stlWorker.js', import.meta.url), {
                type: 'module'
            })
        }

        const taskId = `task_${Math.random().toString(36).substring(7)}`

        const handleMessage = (e) => {
            const { id, success, geometryData, error } = e.data
            if (id !== taskId) return

            if (!success) {
                console.error('[WorkerLoader] Failed to parse STL:', error)
                return
            }

            // Reconstruct the Three.js BufferGeometry on the main thread
            // from the raw Float32 arrays sent by the worker.
            const newGeom = new BufferGeometry()
            newGeom.setAttribute('position', new BufferAttribute(geometryData.positions, 3))

            if (geometryData.normals) {
                newGeom.setAttribute('normal', new BufferAttribute(geometryData.normals, 3))
            } else {
                newGeom.computeVertexNormals() // STLLoader normally does this
            }

            // Compute bounding boxes just like STLLoader does
            newGeom.computeBoundingSphere()
            newGeom.computeBoundingBox()

            // Cache the result
            geometryCache.set(url, newGeom)

            setGeometry(newGeom)

            // Cleanup the listener
            stlWorkerInstance.removeEventListener('message', handleMessage)
        }

        stlWorkerInstance.addEventListener('message', handleMessage)

        // Kick off the worker task
        stlWorkerInstance.postMessage({ url, id: taskId })

        return () => {
            // If the component unmounts before finishing, we cleanup the listener
            // to avoid memory leaks. The worker will still finish but the result is discarded.
            stlWorkerInstance?.removeEventListener('message', handleMessage)
        }
    }, [url, isGLTF])

    return {
        geometry: isGLTF ? gltfMergedGeom : geometry,
        scene: isGLTF ? gltfData?.scene : null
    }
}
