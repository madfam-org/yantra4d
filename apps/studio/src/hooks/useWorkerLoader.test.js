import { renderHook } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useWorkerLoader } from './useWorkerLoader'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'

vi.mock('three/examples/jsm/loaders/GLTFLoader', () => {
    return {
        GLTFLoader: class {
            loadAsync() {
                return Promise.resolve({
                    scene: {
                        updateMatrixWorld: vi.fn(),
                        traverse: vi.fn((cb) => {
                            cb({
                                isMesh: true,
                                geometry: {
                                    clone: () => ({ applyMatrix4: vi.fn() })
                                },
                                matrixWorld: {}
                            })
                        })
                    }
                })
            }
        }
    }
})

describe('useWorkerLoader', () => {
    let MockWorker

    beforeEach(() => {
        MockWorker = class {
            postMessage = vi.fn()
            addEventListener = vi.fn()
            removeEventListener = vi.fn()
            terminate = vi.fn()
        }
        globalThis.Worker = MockWorker
    })

    afterEach(() => {
        vi.restoreAllMocks()
        delete globalThis.Worker
    })

    it('should return null initially for STL', () => {
        const { result } = renderHook(() => useWorkerLoader('test.stl', false))
        expect(result.current).toBeNull()
    })

    it('should call loadAsync for GLTF files', async () => {
        const { result } = renderHook(() => useWorkerLoader('test.gltf', true))

        // Wait for the async effect to settle. Since BufferGeometryUtils.mergeGeometries
        // takes the single mock geometry, it will just return the cloned geometry mock object.
        await vi.waitFor(() => {
            expect(result.current).not.toBeNull()
            expect(result.current.applyMatrix4).toBeDefined()
        })
    })
})
