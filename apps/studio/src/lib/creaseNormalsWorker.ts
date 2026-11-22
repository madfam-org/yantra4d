import { computeCreaseNormals } from './creaseNormals'

/**
 * `computeCreaseNormals` in a worker, so a large mesh does not block the page while it loads
 * (about 60 ms per 100,000 triangles on a desktop CPU, more on a phone). Where no worker can run
 * (tests, an old browser) or the worker fails, the same function runs here instead: the result
 * is identical, only the thread differs.
 *
 * The positions are copied before they are sent, so the caller's array stays usable.
 */

type Job = { resolve: (normals: Float32Array) => void; reject: (error: Error) => void }

const jobs = new Map<number, Job>()
let worker: Worker | null = null
let nextId = 0

function failAll(error: Error) {
    for (const job of jobs.values()) job.reject(error)
    jobs.clear()
    worker?.terminate()
    worker = null
}

function creaseWorker(): Worker {
    if (worker) return worker
    worker = new Worker(new URL('../workers/creaseWorker.js', import.meta.url), { type: 'module' })
    worker.onmessage = (event: MessageEvent<{ id: number; normals?: Float32Array; error?: string }>) => {
        const job = jobs.get(event.data.id)
        if (!job) return
        jobs.delete(event.data.id)
        if (event.data.normals) job.resolve(event.data.normals)
        else job.reject(new Error(event.data.error || 'crease normals failed'))
    }
    worker.onerror = () => failAll(new Error('crease worker crashed'))
    worker.onmessageerror = () => failAll(new Error('crease worker sent a message that could not be read'))
    return worker
}

export function computeCreaseNormalsOffThread(positions: Float32Array, creaseAngleDeg: number): Promise<Float32Array> {
    if (typeof Worker === 'undefined') return Promise.resolve().then(() => computeCreaseNormals(positions, creaseAngleDeg))
    const copy = positions.slice()
    const id = ++nextId
    return new Promise<Float32Array>((resolve, reject) => {
        jobs.set(id, { resolve, reject })
        try {
            creaseWorker().postMessage({ id, positions: copy, creaseAngleDeg }, [copy.buffer])
        } catch (error) {
            jobs.delete(id)
            reject(error as Error)
        }
    }).catch(() => computeCreaseNormals(positions, creaseAngleDeg))
}
