import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import type * as THREE from 'three'
import { addAfterEffect, addEffect, useFrame, useThree } from '@react-three/fiber'
import { createRenderBudget } from '../../lib/renderBudget'
import { getQualityMode, publishReadings, setRenderScale, subscribeQuality } from '../../lib/viewerQuality'

/**
 * The viewer canvas renders on demand (frameloop="demand"). These helpers keep
 * it rendering exactly when something on screen changes.
 */

/** Renders every frame while `active` (animated grid, pulsing preview overlay). */
export function KeepRendering({ active }: { active: boolean }) {
  const invalidate = useThree((s) => s.invalidate)
  useFrame(() => { if (active) invalidate() })
  useEffect(() => { if (active) invalidate() }, [active, invalidate])
  return null
}

/** Requests a frame after every commit, so effect-driven scene changes (clipping planes, material tweaks) reach the screen. */
export function InvalidateOnCommit() {
  const invalidate = useThree((s) => s.invalidate)
  useEffect(() => { invalidate() })
  return null
}

/**
 * Keeps newly loaded geometry hidden until its shader programs are compiled
 * with KHR_parallel_shader_compile (renderer.compileAsync), so the first frame
 * of a model no longer blocks the main thread on a synchronous compile/link.
 * Without the extension compileAsync resolves at once and nothing changes.
 */
export function CompileGate({ signature, children }: { signature: string; children: ReactNode }) {
  const ref = useRef<THREE.Group>(null)
  const gl = useThree((s) => s.gl)
  const camera = useThree((s) => s.camera)
  const scene = useThree((s) => s.scene)
  const invalidate = useThree((s) => s.invalidate)
  const [ready, setReady] = useState<string | null>(null)

  useLayoutEffect(() => {
    const group = ref.current
    if (!group) return
    let live = true
    const show = () => { if (live) { setReady(signature); invalidate() } }
    if (typeof gl.compileAsync === 'function') gl.compileAsync(group, camera, scene).then(show, show)
    else show()
    return () => { live = false }
    // Compile once per geometry; later material changes compile as before.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature])

  return <group ref={ref} visible={ready === signature}>{children}</group>
}

/**
 * Wires the render budget (src/lib/renderBudget.ts: runtime GPU benchmark and
 * adaptive scale) into the R3F frame loop and the Studio quality state.
 */
export default function ViewerPerformance() {
  const gl = useThree((s) => s.gl)
  const scene = useThree((s) => s.scene)
  const camera = useThree((s) => s.camera)
  const invalidate = useThree((s) => s.invalidate)
  const target = useRef<{ scene: THREE.Object3D; camera: THREE.Camera }>({ scene, camera })
  useEffect(() => { target.current = { scene, camera } }, [scene, camera])

  useEffect(() => {
    const budget = createRenderBudget(gl, {
      mode: getQualityMode(),
      onScale: (scale) => { setRenderScale(scale); invalidate() },
      probeTarget: () => target.current,
    })
    setRenderScale(budget.scale)
    const unsubscribe = subscribeQuality(() => budget.setMode(getQualityMode()))
    const removeBefore = addEffect(() => budget.beginFrame())
    const removeAfter = addAfterEffect(() => budget.endFrame())
    const publish = window.setInterval(() => publishReadings(budget.stats()), 1000)
    return () => {
      removeBefore()
      removeAfter()
      unsubscribe()
      window.clearInterval(publish)
      budget.dispose()
    }
  }, [gl, invalidate])

  return null
}
