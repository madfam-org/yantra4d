import { useState, useEffect, useCallback } from 'react'
import { useThree } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import { Vector2, Vector3 } from 'three'

/**
 * MeasureTool — raycaster-based two-click point-to-point measurement.
 * First click sets point A, second click sets point B, computes distance.
 * Renders measurement lines + distance labels via drei Html.
 *
 * @param {boolean} active - whether measure mode is active
 * @param {function} onMeasure - callback({a, b, distance}) when measurement completes
 * @param {Array} measurements - array of existing measurements to display
 */
export default function MeasureTool({ active, onMeasure, measurements = [] }) {
  const { raycaster, camera, scene, gl } = useThree()
  const [pointA, setPointA] = useState(null)

  const handleClick = useCallback((e) => {
    if (!active) return
    const rect = gl.domElement.getBoundingClientRect()
    const mouse = new Vector2(
      ((e.clientX - rect.left) / rect.width) * 2 - 1,
      -((e.clientY - rect.top) / rect.height) * 2 + 1
    )
    raycaster.setFromCamera(mouse, camera)
    const intersects = raycaster.intersectObjects(scene.children, true)
      .filter(i => i.object.isMesh)
    if (intersects.length === 0) return

    const point = intersects[0].point

    if (!pointA) {
      setPointA(point.clone())
      return
    }

    const dist = pointA.distanceTo(point)
    onMeasure?.({ a: pointA.clone(), b: point.clone(), distance: dist })
    setPointA(null)
  }, [active, pointA, raycaster, camera, scene, gl, onMeasure])

  useEffect(() => {
    if (!active) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPointA(null)
      return
    }
    gl.domElement.addEventListener('click', handleClick)
    return () => gl.domElement.removeEventListener('click', handleClick)
  }, [active, handleClick, gl])

  return (
    <>
      {/* Pending first point marker */}
      {pointA && (
        <mesh position={pointA}>
          <sphereGeometry args={[0.5, 16, 16]} />
          <meshBasicMaterial color="#f59e0b" />
        </mesh>
      )}

      {/* Completed measurements */}
      {measurements.map((m, i) => {
        const mid = new Vector3().lerpVectors(m.a, m.b, 0.5)
        return (
          <group key={i}>
            <mesh position={m.a}>
              <sphereGeometry args={[0.3, 12, 12]} />
              <meshBasicMaterial color="#f59e0b" />
            </mesh>
            <mesh position={m.b}>
              <sphereGeometry args={[0.3, 12, 12]} />
              <meshBasicMaterial color="#f59e0b" />
            </mesh>
            <line>
              <bufferGeometry>
                <bufferAttribute
                  attach="attributes-position"
                  count={2}
                  array={new Float32Array([m.a.x, m.a.y, m.a.z, m.b.x, m.b.y, m.b.z])}
                  itemSize={3}
                />
              </bufferGeometry>
              <lineBasicMaterial color="#f59e0b" linewidth={2} />
            </line>
            <Html position={mid} center className="pointer-events-none select-none">
              <div className="bg-background/90 text-amber-500 text-xs px-1.5 py-0.5 rounded shadow-sm border border-amber-500/30 backdrop-blur-sm whitespace-nowrap font-mono">
                {m.distance.toFixed(2)}mm
              </div>
            </Html>
          </group>
        )
      })}
    </>
  )
}
