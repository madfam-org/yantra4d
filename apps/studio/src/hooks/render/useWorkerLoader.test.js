import React from 'react'
import { act, cleanup, renderHook } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { Scene, Mesh, BoxGeometry, MeshStandardMaterial, Texture } from 'three'

const { loadAsync, bearerHeaderForSameOrigin } = vi.hoisted(() => ({ loadAsync: vi.fn(), bearerHeaderForSameOrigin: vi.fn() }))
vi.mock('three/examples/jsm/loaders/GLTFLoader', () => ({
  GLTFLoader: class { loadAsync = loadAsync; setRequestHeader = vi.fn() },
}))
vi.mock('../../lib/januaSso', () => ({ bearerHeaderForSameOrigin }))

let useWorkerLoader, workers
class MockWorker extends EventTarget {
  sent = []
  constructor() { super(); workers.push(this) }
  postMessage(message) { this.sent.push(message) }
  terminate = vi.fn()
  complete(index, size = 1) {
    this.dispatchEvent(new MessageEvent('message', { data: {
      id: this.sent[index].id, success: true,
      geometryData: { positions: new Float32Array([0, 0, 0, size, 0, 0, 0, size, 0]) },
    } }))
  }
}
function scene() {
  const value = new Scene()
  value.add(new Mesh(new BoxGeometry(), new MeshStandardMaterial()))
  return { scene: value }
}

beforeEach(async () => {
  vi.resetModules()
  vi.useFakeTimers()
  workers = []
  vi.stubGlobal('Worker', MockWorker)
  loadAsync.mockReset()
  bearerHeaderForSameOrigin.mockReset().mockReturnValue(null)
  vi.spyOn(console, 'error').mockImplementation(() => {})
  ;({ useWorkerLoader } = await import('./useWorkerLoader'))
})
afterEach(() => {
  cleanup()
  vi.clearAllTimers()
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('useWorkerLoader lifecycle', () => {
  it('returns no geometry or scene for an absent GLB URL', () => {
    const { result } = renderHook(() => useWorkerLoader(undefined, true))
    expect(result.current).toEqual({ geometry: null, scene: null })
    expect(loadAsync).not.toHaveBeenCalled()
  })

  it('settles synchronous worker dispatch failures and permits a new worker', async () => {
    vi.spyOn(MockWorker.prototype, 'postMessage').mockImplementationOnce(() => { throw new Error('dispatch failed') })
    const first = renderHook(() => useWorkerLoader('dispatch.stl'))
    await act(async () => {})
    expect(workers[0].terminate).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(0)
    first.unmount()
    const next = renderHook(() => useWorkerLoader('dispatch.stl'))
    await act(async () => workers[1].complete(0))
    expect(next.result.current.geometry).not.toBeNull()
  })

  it('keeps a shared STL request alive when the initiating consumer unmounts', async () => {
    const first = renderHook(() => useWorkerLoader('shared.stl'))
    const second = renderHook(() => useWorkerLoader('shared.stl'))
    first.unmount()
    expect(workers[0].sent).toHaveLength(1)
    await act(async () => workers[0].complete(0))
    expect(second.result.current.geometry?.getAttribute('position').count).toBe(3)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('settles the shared request across StrictMode effect cleanup/replay', async () => {
    const { result } = renderHook(() => useWorkerLoader('strict.stl'), {
      wrapper: ({ children }) => React.createElement(React.StrictMode, null, children),
    })
    await act(async () => workers[0].complete(0))
    expect(result.current.geometry).not.toBeNull()
    expect(workers[0].sent).toHaveLength(1)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('does not show previous STL geometry while a new URL loads or after clearing', async () => {
    const { result, rerender } = renderHook(({ url }) => useWorkerLoader(url), { initialProps: { url: 'old.stl' } })
    await act(async () => workers[0].complete(0))
    expect(result.current.geometry).not.toBeNull()
    rerender({ url: 'new.stl' })
    expect(result.current.geometry).toBeNull()
    await act(async () => workers[0].complete(1, 2))
    expect(result.current.geometry.boundingBox.max.x).toBe(2)
    rerender({ url: null })
    expect(result.current.geometry).toBeNull()
  })

  it('ignores a late shared STL result after the consumer changes URL', async () => {
    const owner = renderHook(() => useWorkerLoader('slow.stl'))
    const { result, rerender } = renderHook(({ url }) => useWorkerLoader(url), { initialProps: { url: 'slow.stl' } })
    rerender({ url: 'fast.stl' })
    await act(async () => workers[0].complete(1, 2))
    await act(async () => workers[0].complete(0, 1))
    expect(result.current.geometry.boundingBox.max.x).toBe(2)
    expect(owner.result.current.geometry.boundingBox.max.x).toBe(1)
  })

  it('ignores late GLB results and hides stale scenes when switching formats', async () => {
    let resolveOld, resolveNew
    loadAsync.mockReturnValueOnce(new Promise(r => { resolveOld = r })).mockReturnValueOnce(new Promise(r => { resolveNew = r }))
    const { result, rerender } = renderHook(({ url, glb }) => useWorkerLoader(url, glb), { initialProps: { url: 'old.glb', glb: true } })
    rerender({ url: 'new.glb', glb: true })
    const newer = scene()
    await act(async () => resolveNew(newer))
    await act(async () => resolveOld(scene()))
    expect(result.current.scene).toBe(newer.scene)
    rerender({ url: 'pending.stl', glb: false })
    expect(result.current).toEqual({ geometry: null, scene: null })
  })

  it('releases failed worker requests so remount can retry', async () => {
    const first = renderHook(() => useWorkerLoader('failed.stl'))
    await act(async () => workers[0].dispatchEvent(new ErrorEvent('error', { message: 'crash' })))
    first.unmount()
    const second = renderHook(() => useWorkerLoader('failed.stl'))
    expect(workers).toHaveLength(2)
    await act(async () => workers[1].complete(0))
    expect(second.result.current.geometry).not.toBeNull()
  })

  it('clears all pending tasks when a timed-out singleton is discarded', async () => {
    renderHook(() => useWorkerLoader('timeout-one.stl'))
    await act(async () => vi.advanceTimersByTimeAsync(1000))
    renderHook(() => useWorkerLoader('timeout-two.stl'))
    await act(async () => vi.advanceTimersByTimeAsync(119000))
    expect(workers[0].terminate).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(0)
    renderHook(() => useWorkerLoader('timeout-two.stl'))
    expect(workers).toHaveLength(2)
  })
})


describe('consumer-owned viewer resources', () => {
  it('does not reuse cached payloads between different bearer identities', async () => {
    bearerHeaderForSameOrigin.mockReturnValue('Bearer synthetic-first')
    const first = renderHook(() => useWorkerLoader('/private.stl'))
    await act(async () => workers[0].complete(0))
    first.unmount()
    bearerHeaderForSameOrigin.mockReturnValue('Bearer synthetic-second')
    const second = renderHook(() => useWorkerLoader('/private.stl'))
    expect(workers[0].sent).toHaveLength(2)
    expect(workers[0].sent[1].authHeader).toBe('Bearer synthetic-second')
    expect(second.result.current.geometry).toBeNull()
    await act(async () => workers[0].complete(1, 2))
    expect(second.result.current.geometry.boundingBox.max.x).toBe(2)
  })

  it('evicts old payloads and releases displayed geometries over repeated model changes', async () => {
    const view = renderHook(({ url }) => useWorkerLoader(url), { initialProps: { url: 'model-0.stl' } })
    const released = []
    for (let i = 0; i < 64; i++) {
      if (i) view.rerender({ url: `model-${i}.stl` })
      await act(async () => workers[0].complete(i))
      released.push(vi.spyOn(view.result.current.geometry, 'dispose'))
    }
    view.rerender({ url: null })
    expect(released.every(release => release.mock.calls.length === 1)).toBe(true)
    expect(view.result.current.geometry).toBeNull()
    view.rerender({ url: 'model-0.stl' })
    expect(workers[0].sent).toHaveLength(65)
    await act(async () => workers[0].complete(64))
  })

  it('shares parsing without sharing mutable consumer geometry', async () => {
    const first = renderHook(() => useWorkerLoader('owned.stl'))
    const second = renderHook(() => useWorkerLoader('owned.stl'))
    await act(async () => workers[0].complete(0))
    expect(workers[0].sent).toHaveLength(1)
    expect(first.result.current.geometry).not.toBe(second.result.current.geometry)
    first.result.current.geometry.attributes.position.array[0] = 42
    expect(second.result.current.geometry.attributes.position.array[0]).toBe(0)
    const releaseFirst = vi.spyOn(first.result.current.geometry, 'dispose')
    const releaseSecond = vi.spyOn(second.result.current.geometry, 'dispose')
    first.unmount()
    expect(releaseFirst).toHaveBeenCalledTimes(1)
    expect(releaseSecond).not.toHaveBeenCalled()
    second.unmount()
    expect(releaseSecond).toHaveBeenCalledTimes(1)
  })

  it('disposes the previous STL on URL replacement and does not resurface it on A/B/A', async () => {
    const view = renderHook(({ url }) => useWorkerLoader(url), { initialProps: { url: 'a.stl' } })
    await act(async () => workers[0].complete(0))
    const original = view.result.current.geometry
    const release = vi.spyOn(original, 'dispose')
    view.rerender({ url: 'b.stl' })
    expect(release).toHaveBeenCalledTimes(1)
    view.rerender({ url: 'a.stl' })
    expect(view.result.current.geometry).toBeNull()
    await act(async () => {})
    expect(view.result.current.geometry).not.toBe(original)
    expect(view.result.current.geometry).not.toBeNull()
  })

  it('disposes a loaded GLB, analysis geometry, shared material and texture once', async () => {
    const data = scene()
    const mesh = data.scene.children[0]
    const bitmap = { close: vi.fn() }
    const texture = new Texture(bitmap)
    mesh.material.map = texture
    data.scene.add(new Mesh(mesh.geometry, mesh.material))
    const geometryDispose = vi.spyOn(mesh.geometry, 'dispose')
    const materialDispose = vi.spyOn(mesh.material, 'dispose')
    const textureDispose = vi.spyOn(texture, 'dispose')
    loadAsync.mockResolvedValue(data)
    const view = renderHook(() => useWorkerLoader('owned.glb', true))
    await act(async () => {})
    const mergedDispose = vi.spyOn(view.result.current.geometry, 'dispose')
    view.unmount()
    expect(geometryDispose).toHaveBeenCalledTimes(1)
    expect(materialDispose).toHaveBeenCalledTimes(1)
    expect(textureDispose).toHaveBeenCalledTimes(1)
    expect(bitmap.close).toHaveBeenCalledTimes(1)
    expect(mergedDispose).toHaveBeenCalledTimes(1)
  })

  it('disposes a late GLB without publishing it after unmount', async () => {
    let complete
    loadAsync.mockReturnValue(new Promise(resolve => { complete = resolve }))
    const view = renderHook(() => useWorkerLoader('late.glb', true))
    const data = scene()
    const release = vi.spyOn(data.scene.children[0].geometry, 'dispose')
    view.unmount()
    await act(async () => complete(data))
    expect(release).toHaveBeenCalledTimes(1)
  })
})
