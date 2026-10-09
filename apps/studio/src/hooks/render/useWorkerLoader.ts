import { useState, useEffect, useMemo } from 'react'
import { BufferGeometry, Scene } from 'three'
// @ts-expect-error three.js examples lack type declarations in this project's TS config
import { GLTFLoader, GLTF } from 'three/examples/jsm/loaders/GLTFLoader'
import { STLPayloadCache, type STLPayload } from '../../lib/stlPayloadCache'
import { createSTLGeometry, mergeGLTFGeometry, disposeGLTF } from '../../lib/viewerResources'
import { bearerHeaderForSameOrigin } from '../../lib/januaSso'

interface WorkerMessage {
  id: string
  success: boolean
  geometryData: STLPayload
  error?: string
}

interface WorkerLoaderResult {
  geometry: BufferGeometry | null
  scene: Scene | null
}

// We create a singleton worker so we don't spin up dozens of threads.
// Notice the ?worker syntax which Vite requires to bundle it correctly.
let stlWorkerInstance: Worker | null = null

// Completed CPU payloads are bounded; in-flight parsing is shared separately.
const payloadCache = new STLPayloadCache()
const pendingLoads = new Map<string, Promise<STLPayload>>()

// Tasks belong to the shared loader, not to the component that first asked.
// Unmounting one consumer must not remove the completion listener for the others.
const pendingTasks = new Map<Worker, Set<(message: string) => void>>()

function discardWorker(worker: Worker, message: string): void {
    if (stlWorkerInstance === worker) stlWorkerInstance = null
    for (const reject of [...(pendingTasks.get(worker) ?? [])]) reject(message)
    try { worker.terminate() } catch { /* already gone */ }
}

function loadSTL(url: string): Promise<STLPayload> {
    const authHeader = bearerHeaderForSameOrigin(url)
    // Same URL under a different session must never reuse a private payload.
    const key = JSON.stringify([url, authHeader ?? null])
    const cached = payloadCache.get(key)
    if (cached) return Promise.resolve(cached)
    const pending = pendingLoads.get(key)
    if (pending) return pending

    const promise = new Promise<STLPayload>((resolve, reject) => {
        if (!stlWorkerInstance) {
            stlWorkerInstance = new Worker(new URL('../../workers/stlWorker.js', import.meta.url), { type: 'module' })
        }
        const worker = stlWorkerInstance
        const taskId = `task_${Math.random().toString(36).substring(7)}`
        let settled = false
        const tasks = pendingTasks.get(worker) ?? new Set<(message: string) => void>()
        pendingTasks.set(worker, tasks)
        const detach = () => {
            worker.removeEventListener('message', handleMessage)
            worker.removeEventListener('error', handleError)
            worker.removeEventListener('messageerror', handleMessageError)
            clearTimeout(timer)
            tasks.delete(fail)
            if (tasks.size === 0) pendingTasks.delete(worker)
        }
        const fail = (message: string) => {
            if (settled) return
            settled = true
            detach()
            reject(new Error(message))
        }
        const handleError = (event: ErrorEvent) => discardWorker(worker, `STL worker failed: ${event.message || 'unknown error'}`)
        const handleMessageError = () => discardWorker(worker, 'STL worker sent a message that could not be deserialized')
        const timer = setTimeout(() => discardWorker(worker, 'STL parse timed out after 120s'), 120_000)
        const handleMessage = (event: MessageEvent<WorkerMessage>) => {
            const { id, success, geometryData, error } = event.data
            if (id !== taskId || settled) return
            if (!success) return fail(`Failed to parse STL: ${error}`)
            if (!(geometryData?.positions instanceof Float32Array)
                || geometryData.positions.length % 3 !== 0
                || (geometryData.normals != null && (!(geometryData.normals instanceof Float32Array)
                    || geometryData.normals.length !== geometryData.positions.length))) {
                return fail('STL worker returned invalid geometry arrays')
            }
            settled = true
            detach()
            resolve(geometryData)
        }
        tasks.add(fail)
        worker.addEventListener('message', handleMessage)
        worker.addEventListener('error', handleError)
        worker.addEventListener('messageerror', handleMessageError)
        try {
            worker.postMessage({ url, id: taskId, authHeader })
        } catch (error) {
            discardWorker(worker, `STL worker could not start task: ${String(error)}`)
        }
    }).then(payload => {
        pendingLoads.delete(key)
        payloadCache.set(key, payload)
        return payload
    }, error => {
        pendingLoads.delete(key)
        throw error
    })
    pendingLoads.set(key, promise)
    return promise
}

/** Load the current request; this effect owns all displayed Three.js resources. */
export function useWorkerLoader(url: string | null | undefined, isGLTF: boolean = false): WorkerLoaderResult {
    // Identity distinguishes A/B/A transitions and never resurrects disposed A.
    const request = useMemo(() => ({ url, isGLTF }), [url, isGLTF])
    const [result, setResult] = useState<(WorkerLoaderResult & { request: typeof request }) | null>(null)
    // Drop the state reference too, including when a URL is cleared indefinitely.
    // The previous effect still owns its cleanup until React commits this change.
    if (result && result.request !== request) setResult(null)

    useEffect(() => {
        if (!request.url) return
        let active = true
        let release: (() => void) | undefined
        const reportError = (error: unknown) => { if (active) console.error('[WorkerLoader]', error) }
        if (request.isGLTF) {
            const loader = new GLTFLoader()
            const auth = bearerHeaderForSameOrigin(request.url)
            if (auth) loader.setRequestHeader({ Authorization: auth })
            loader.loadAsync(request.url).then((data: GLTF) => {
                if (!active) { disposeGLTF(data); return }
                let geometry: BufferGeometry | null = null
                try {
                    geometry = mergeGLTFGeometry(data.scene)
                } catch (error) {
                    disposeGLTF(data)
                    throw error
                }
                release = () => { geometry?.dispose(); disposeGLTF(data) }
                setResult({ request, geometry, scene: data.scene })
            }).catch(reportError)
        } else {
            loadSTL(request.url).then(payload => {
                if (!active) return
                const geometry = createSTLGeometry(payload)
                release = () => geometry.dispose()
                setResult({ request, geometry, scene: null })
            }).catch(reportError)
        }
        return () => { active = false; release?.() }
    }, [request])

    return result?.request === request
        ? { geometry: result.geometry, scene: result.scene }
        : { geometry: null, scene: null }
}
