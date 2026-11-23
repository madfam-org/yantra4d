import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { computeCreaseNormals } from './creaseNormals'

const fold = new Float32Array([
    0, 0, 0, 1, 0, 0, 0, 1, 0,
    0, 0, 0, 0, 1, 0, -Math.cos(0.3), 0, -Math.sin(0.3),
])

type Reply = (data: { id: number; positions: Float32Array; creaseAngleDeg: number }, worker: FakeWorker) => void
let reply: Reply
let created: FakeWorker[]
class FakeWorker {
    onmessage: ((event: MessageEvent) => void) | null = null
    onerror: (() => void) | null = null
    onmessageerror: (() => void) | null = null
    sent: unknown[] = []
    terminate = vi.fn()
    constructor() { created.push(this) }
    postMessage(data: { id: number; positions: Float32Array; creaseAngleDeg: number }, transfer: Transferable[] = []) {
        // Transfer like a real worker, so a caller buffer that is sent away shows as detached.
        const delivered = structuredClone(data, { transfer })
        this.sent.push(delivered)
        queueMicrotask(() => reply(delivered, this))
    }
}

beforeEach(() => {
    vi.resetModules()
    created = []
    vi.stubGlobal('Worker', FakeWorker)
})
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

describe('computeCreaseNormalsOffThread', () => {
    it('returns what the worker computed and leaves the caller its positions', async () => {
        reply = (data, worker) => worker.onmessage?.({ data: { id: data.id, normals: computeCreaseNormals(data.positions, data.creaseAngleDeg) } } as MessageEvent)
        const { computeCreaseNormalsOffThread } = await import('./creaseNormalsWorker')
        const positions = fold.slice()
        const normals = await computeCreaseNormalsOffThread(positions, 20)
        expect([...normals]).toEqual([...computeCreaseNormals(fold, 20)])
        expect(positions.byteLength).toBeGreaterThan(0)
        expect([...positions]).toEqual([...fold])
        expect(created).toHaveLength(1)
        await computeCreaseNormalsOffThread(positions, 20)
        expect(created).toHaveLength(1)
    })

    it('falls back to this thread when the worker reports an error', async () => {
        reply = (data, worker) => worker.onmessage?.({ data: { id: data.id, error: 'boom' } } as MessageEvent)
        const { computeCreaseNormalsOffThread } = await import('./creaseNormalsWorker')
        expect([...await computeCreaseNormalsOffThread(fold, 20)]).toEqual([...computeCreaseNormals(fold, 20)])
    })

    it('falls back for every pending job when the worker crashes, and starts a new one next time', async () => {
        reply = (_data, worker) => worker.onerror?.()
        const { computeCreaseNormalsOffThread } = await import('./creaseNormalsWorker')
        const [a, b] = await Promise.all([computeCreaseNormalsOffThread(fold, 20), computeCreaseNormalsOffThread(fold, 40)])
        expect([...a]).toEqual([...computeCreaseNormals(fold, 20)])
        expect([...b]).toEqual([...computeCreaseNormals(fold, 40)])
        expect(created[0].terminate).toHaveBeenCalled()
        reply = (data, worker) => worker.onmessage?.({ data: { id: data.id, normals: computeCreaseNormals(data.positions, data.creaseAngleDeg) } } as MessageEvent)
        await computeCreaseNormalsOffThread(fold, 20)
        expect(created).toHaveLength(2)
    })

    it('runs on this thread where there is no Worker', async () => {
        vi.stubGlobal('Worker', undefined)
        const { computeCreaseNormalsOffThread } = await import('./creaseNormalsWorker')
        expect([...await computeCreaseNormalsOffThread(fold, 20)]).toEqual([...computeCreaseNormals(fold, 20)])
    })
    it('gives up on a worker that never answers, and the next call gets a fresh one', async () => {
        vi.useFakeTimers()
        reply = () => {}
        const { computeCreaseNormalsOffThread, CREASE_WORKER_DEADLINE_MS } = await import('./creaseNormalsWorker')
        const pending = computeCreaseNormalsOffThread(fold, 20)
        await vi.advanceTimersByTimeAsync(CREASE_WORKER_DEADLINE_MS + 1)
        expect([...await pending]).toEqual([...computeCreaseNormals(fold, 20)])
        expect(created[0].terminate).toHaveBeenCalled()
        reply = (data, worker) => worker.onmessage?.({ data: { id: data.id, normals: computeCreaseNormals(data.positions, data.creaseAngleDeg) } } as MessageEvent)
        await computeCreaseNormalsOffThread(fold, 20)
        expect(created).toHaveLength(2)
    })

    it('ignores a late error from a worker it has already replaced', async () => {
        reply = (_data, worker) => worker.onerror?.()
        const { computeCreaseNormalsOffThread } = await import('./creaseNormalsWorker')
        await computeCreaseNormalsOffThread(fold, 20)
        const first = created[0]
        let answer: (() => void) | null = null
        reply = (data, worker) => { answer = () => worker.onmessage?.({ data: { id: data.id, normals: new Float32Array(data.positions.length).fill(7) } } as MessageEvent) }
        const pending = computeCreaseNormalsOffThread(fold, 20)
        await new Promise(resolve => setTimeout(resolve, 0))
        first.onerror?.()
        answer!()
        expect((await pending)[0]).toBe(7)
        expect(created[1].terminate).not.toHaveBeenCalled()
    })
})
