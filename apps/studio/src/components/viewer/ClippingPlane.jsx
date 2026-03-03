import { useMemo, useEffect } from 'react'
import { useThree } from '@react-three/fiber'
import { Vector3, Plane, DoubleSide } from 'three'

/**
 * ClippingPlane — applies a single clipping plane to the renderer.
 * Renders a semi-transparent visual indicator plane so users can see
 * where the cross-section cut is positioned.
 *
 * @param {'x'|'y'|'z'} axis - which axis the plane normal aligns to
 * @param {number} position - 0..1 normalized position between bbox min and max
 * @param {import('three').Box3|null} bbox - scene bounding box (THREE.Box3)
 */
export default function ClippingPlane({ axis = 'z', position = 0.5, bbox }) {
  const { gl } = useThree()

  const { plane, planePos, rotation } = useMemo(() => {
    const normal = new Vector3(
      axis === 'x' ? -1 : 0,
      axis === 'y' ? -1 : 0,
      axis === 'z' ? -1 : 0
    )
    const min = bbox?.min?.[axis] ?? 0
    const max = bbox?.max?.[axis] ?? 100
    const d = min + (max - min) * position

    const p = new Plane(normal, d)

    // Position the visual indicator
    const pos = [
      axis === 'x' ? d : (bbox ? (bbox.min.x + bbox.max.x) / 2 : 0),
      axis === 'y' ? d : (bbox ? (bbox.min.y + bbox.max.y) / 2 : 0),
      axis === 'z' ? d : (bbox ? (bbox.min.z + bbox.max.z) / 2 : 0),
    ]

    // Rotation to align plane with axis
    const rot = axis === 'x'
      ? [0, Math.PI / 2, 0]
      : axis === 'y'
        ? [Math.PI / 2, 0, 0]
        : [0, 0, 0]

    return { plane: p, planePos: pos, rotation: rot }
  }, [axis, position, bbox])

  // Size the indicator to the bounding box
  const planeSize = useMemo(() => {
    if (!bbox) return [200, 200]
    const size = bbox.getSize(new Vector3())
    const maxDim = Math.max(size.x, size.y, size.z) * 1.2
    return [maxDim, maxDim]
  }, [bbox])

  // gl.clippingPlanes is a Three.js renderer property (external system mutation)
  useEffect(() => {
    gl.clippingPlanes = [plane] // eslint-disable-line react-hooks/immutability
    return () => {
      gl.clippingPlanes = []
    }
  }, [gl, plane])

  return (
    <mesh position={planePos} rotation={rotation}>
      <planeGeometry args={planeSize} />
      <meshBasicMaterial
        color="#06b6d4"
        transparent
        opacity={0.1}
        side={DoubleSide}
        depthWrite={false}
      />
    </mesh>
  )
}
