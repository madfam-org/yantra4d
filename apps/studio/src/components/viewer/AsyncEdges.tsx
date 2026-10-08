import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { Line } from '@react-three/drei'
import { useThree } from '@react-three/fiber'
import type { LineSegments2 } from 'three-stdlib'

/**
 * Drop-in for drei's <Edges> that computes the feature edges in a worker.
 *
 * drei's <Edges> runs `new EdgesGeometry()` in a layout effect, on the main
 * thread, right after a model mounts (about 0.9 s for 100k triangles on a
 * 6-core desktop CPU). This renders the same drei <Line segments>
 * with the same EdgesGeometry output, so the outline looks identical; it just
 * appears once the worker answers. Results are cached per geometry.
 */

type Job = { resolve: (edges: Float32Array) => void; reject: (error: Error) => void }

const cache = new WeakMap<THREE.BufferGeometry, Map<number, Promise<Float32Array>>>()
const jobs = new Map<number, Job>()
let worker: Worker | null = null
let nextId = 0

function computeInPlace(geometry: THREE.BufferGeometry, threshold: number): Float32Array {
  return new THREE.EdgesGeometry(geometry, threshold).attributes.position.array as Float32Array
}

function failAll(error: Error) {
  for (const job of jobs.values()) job.reject(error)
  jobs.clear()
  worker?.terminate()
  worker = null
}

function edgesWorker(): Worker {
  if (worker) return worker
  worker = new Worker(new URL('../../workers/edgesWorker.js', import.meta.url), { type: 'module' })
  worker.onmessage = (event: MessageEvent<{ id: number; edges?: Float32Array; error?: string }>) => {
    const job = jobs.get(event.data.id)
    if (!job) return
    jobs.delete(event.data.id)
    if (event.data.edges) job.resolve(event.data.edges)
    else job.reject(new Error(event.data.error || 'edge extraction failed'))
  }
  worker.onerror = () => failAll(new Error('edge worker crashed'))
  return worker
}

function computeInWorker(geometry: THREE.BufferGeometry, threshold: number): Promise<Float32Array> {
  const position = geometry.getAttribute('position')
  const plain = position && !('isInterleavedBufferAttribute' in position && position.isInterleavedBufferAttribute)
    && position.itemSize === 3 && !position.normalized && position.array instanceof Float32Array
  if (typeof Worker === 'undefined' || !plain) {
    return Promise.resolve().then(() => computeInPlace(geometry, threshold))
  }
  const positions = (position.array as Float32Array).slice(0, position.count * 3)
  const index = geometry.index ? Uint32Array.from(geometry.index.array) : null
  const transfer: Transferable[] = index ? [positions.buffer, index.buffer] : [positions.buffer]
  const id = ++nextId
  return new Promise<Float32Array>((resolve, reject) => {
    jobs.set(id, { resolve, reject })
    try {
      edgesWorker().postMessage({ id, positions, index, threshold }, transfer)
    } catch (error) {
      jobs.delete(id)
      reject(error as Error)
    }
  }).catch(() => computeInPlace(geometry, threshold))
}

/** Feature-edge segment positions for a geometry, computed once per threshold. */
export function computeEdges(geometry: THREE.BufferGeometry, threshold: number): Promise<Float32Array> {
  let byThreshold = cache.get(geometry)
  if (!byThreshold) {
    byThreshold = new Map()
    cache.set(geometry, byThreshold)
  }
  let job = byThreshold.get(threshold)
  if (!job) {
    job = computeInWorker(geometry, threshold)
    byThreshold.set(threshold, job)
  }
  return job
}

const PLACEHOLDER: number[] = [0, 0, 0, 1, 0, 0]
const noRaycast = () => null

interface AsyncEdgesProps {
  geometry: THREE.BufferGeometry
  threshold?: number
  color: string
}

export default function AsyncEdges({ geometry, threshold = 15, color }: AsyncEdgesProps) {
  const ref = useRef<LineSegments2>(null)
  const invalidate = useThree((s) => s.invalidate)
  const [shownFor, setShownFor] = useState<THREE.BufferGeometry | null>(null)

  useEffect(() => {
    let live = true
    computeEdges(geometry, threshold).then((points) => {
      const line = ref.current
      if (!live || !line) return
      line.geometry.setPositions(points)
      line.geometry.attributes.instanceStart.needsUpdate = true
      line.geometry.attributes.instanceEnd.needsUpdate = true
      line.computeLineDistances()
      setShownFor(geometry)
      invalidate()
    })
    return () => { live = false }
  }, [geometry, threshold, invalidate])

  return (
    <Line
      ref={ref}
      segments
      points={PLACEHOLDER}
      color={color}
      visible={shownFor === geometry}
      raycast={noRaycast}
    />
  )
}
