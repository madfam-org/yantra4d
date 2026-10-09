import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, act } from '@testing-library/react'
import * as THREE from 'three'

const invalidate = vi.fn()
const setPositions = vi.fn()
const computeLineDistances = vi.fn()
vi.mock('@react-three/fiber', () => ({ useThree: (sel) => sel({ invalidate }) }))
vi.mock('@react-three/drei', async () => {
  const React = await import('react')
  return {
    Line: React.forwardRef(function Line(props, ref) {
      React.useImperativeHandle(ref, () => ({
        geometry: { setPositions, attributes: { instanceStart: {}, instanceEnd: {} } },
        computeLineDistances,
      }))
      return <div data-testid="edges" data-visible={String(props.visible)} />
    }),
  }
})

import AsyncEdges, { computeEdges } from './AsyncEdges'

const box = () => new THREE.BoxGeometry(1, 1, 1)
const expected = (g, t) => Array.from(new THREE.EdgesGeometry(g, t).attributes.position.array)

afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks() })

describe('computeEdges', () => {
  it('matches EdgesGeometry when no worker is available and caches per threshold', async () => {
    vi.stubGlobal('Worker', undefined)
    const g = box()
    const first = computeEdges(g, 15)
    expect(computeEdges(g, 15)).toBe(first)
    expect(Array.from(await first)).toEqual(expected(g, 15))
    expect(Array.from(await computeEdges(g, 30))).toEqual(expected(g, 30))
  })

  it('posts a copy of the positions to the worker and resolves with its answer', async () => {
    const sent = []
    class MockWorker {
      constructor() { MockWorker.last = this }
      postMessage(message) {
        sent.push(message)
        const edges = new Float32Array([1, 2, 3, 4, 5, 6])
        queueMicrotask(() => this.onmessage({ data: { id: message.id, edges } }))
      }
      terminate() {}
    }
    vi.stubGlobal('Worker', MockWorker)
    const g = box()
    const edges = await computeEdges(g, 15)
    expect(Array.from(edges)).toEqual([1, 2, 3, 4, 5, 6])
    expect(sent[0].threshold).toBe(15)
    expect(sent[0].positions).not.toBe(g.getAttribute('position').array)
    expect(sent[0].index).toBeInstanceOf(Uint32Array)
    // A worker error answer falls back to the in-place computation.
    MockWorker.prototype.postMessage = function (message) {
      queueMicrotask(() => this.onmessage({ data: { id: message.id, error: 'boom' } }))
    }
    const g2 = box()
    expect(Array.from(await computeEdges(g2, 15))).toEqual(expected(g2, 15))
    // A crashed worker rejects pending jobs, which also fall back.
    MockWorker.prototype.postMessage = function () { queueMicrotask(() => this.onerror(new Event('error'))) }
    const g3 = box()
    expect(Array.from(await computeEdges(g3, 15))).toEqual(expected(g3, 15))
  })
})

describe('<AsyncEdges>', () => {
  it('stays hidden until the edges arrive, then fills the line and requests a frame', async () => {
    vi.stubGlobal('Worker', undefined)
    const g = box()
    const { getByTestId } = render(<AsyncEdges geometry={g} color="#fff" />)
    expect(getByTestId('edges').dataset.visible).toBe('false')
    await act(async () => { await computeEdges(g, 15) })
    expect(setPositions).toHaveBeenCalledTimes(1)
    expect(computeLineDistances).toHaveBeenCalled()
    expect(invalidate).toHaveBeenCalled()
    expect(getByTestId('edges').dataset.visible).toBe('true')
  })
})
