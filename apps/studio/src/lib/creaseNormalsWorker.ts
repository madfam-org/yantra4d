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

/** A worker that has not answered by then is presumed dead, as with the STL worker. */
export const CREASE_WORKER_DEADLINE_MS = 120_000

const jobs = new Map<number, Job>()
let worker: Worker | null = null
let deadline: ReturnType<typeof setTimeout> | null = null
let nextId = 0

/** Settle every pending job (each falls back to this thread) and retire `which`. */
function failAll(which: Worker, error: Error) {
    if (worker !== which) return
    worker = null
    if (deadline) clearTimeout(deadline)
    deadline = null
    which.terminate()
    const pending = [...jobs.values()]
    jobs.clear()
    for (const job of pending) job.reject(error)
}

/** One deadline for the worker, restarted whenever it answers and cleared when it is idle. */
function armDeadline(which: Worker) {
    if (deadline) clearTimeout(deadline)
    deadline = jobs.size > 0
        ? setTimeout(() => failAll(which, new Error('crease worker did not answer in time')), CREASE_WORKER_DEADLINE_MS)
        : null
}

function creaseWorker(): Worker {
    if (worker) return worker
    const created = new Worker(new URL('../workers/creaseWorker.js', import.meta.url), { type: 'module' })
    worker = created
    created.onmessage = (event: MessageEvent<{ id: number; normals?: Float32Array; error?: string }>) => {
        if (worker !== created) return
        const job = jobs.get(event.data.id)
        if (!job) return
        jobs.delete(event.data.id)
        armDeadline(created)
        if (event.data.normals) job.resolve(event.data.normals)
        else job.reject(new Error(event.data.error || 'crease normals failed'))
    }
    created.onerror = () => failAll(created, new Error('crease worker crashed'))
    created.onmessageerror = () => failAll(created, new Error('crease worker sent a message that could not be read'))
    return created
}

export function computeCreaseNormalsOffThread(positions: Float32Array, creaseAngleDeg: number): Promise<Float32Array> {
    if (typeof Worker === 'undefined') return Promise.resolve().then(() => computeCreaseNormals(positions, creaseAngleDeg))
    const copy = positions.slice()
    const id = ++nextId
    return new Promise<Float32Array>((resolve, reject) => {
        jobs.set(id, { resolve, reject })
        try {
            const target = creaseWorker()
            target.postMessage({ id, positions: copy, creaseAngleDeg }, [copy.buffer])
            armDeadline(target)
        } catch (error) {
            jobs.delete(id)
            reject(error as Error)
        }
    }).catch(() => computeCreaseNormals(positions, creaseAngleDeg))
}
