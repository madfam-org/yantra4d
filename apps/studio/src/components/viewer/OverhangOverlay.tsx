import { useMemo } from 'react'
import { Color } from 'three'

/**
 * OverhangOverlay — visualizes overhang angles as a colored point cloud.
 * Maps overhang angle values to a green→yellow→red color ramp.
 *
 * Green (0-30°) → Yellow (30-45°) → Red (>45°)
 *
 * @param {Array} points - [[x,y,z], ...] sample points
 * @param {Array} angles - [number, ...] overhang angle at each point (degrees)
 * @param {number} threshold - overhang threshold in degrees (default 45)
 */
interface OverhangOverlayProps {
  points?: number[][]
  angles?: number[]
  threshold?: number
}

export default function OverhangOverlay({
  points = [],
  angles = [],
  threshold = 45,
}: OverhangOverlayProps) {
  const { colorArray, positionArray } = useMemo(() => {
    if (!points.length || !angles.length) {
      return { colorArray: new Float32Array(0), positionArray: new Float32Array(0) }
    }

    const positions = new Float32Array(points.length * 3)
    const colors = new Float32Array(points.length * 3)

    const green = new Color('#22c55e')
    const yellow = new Color('#eab308')
    const red = new Color('#ef4444')

    // Color ramp: 0→30° green, 30→threshold yellow blend, >threshold red
    const yellowStart = threshold * 0.67

    for (let i = 0; i < points.length; i++) {
      const p = points[i]
      positions[i * 3] = p[0]
      positions[i * 3 + 1] = p[1]
      positions[i * 3 + 2] = p[2]

      const angle = angles[i]
      let color
      if (angle <= yellowStart) {
        color = green
      } else if (angle <= threshold) {
        const frac = (angle - yellowStart) / (threshold - yellowStart)
        color = frac < 0.5
          ? new Color().lerpColors(green, yellow, frac * 2)
          : new Color().lerpColors(yellow, red, (frac - 0.5) * 2)
      } else {
        color = red
      }

      colors[i * 3] = color.r
      colors[i * 3 + 1] = color.g
      colors[i * 3 + 2] = color.b
    }

    return { colorArray: colors, positionArray: positions }
  }, [points, angles, threshold])

  if (positionArray.length === 0) return null

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positionArray, 3]}
        />
        <bufferAttribute
          attach="attributes-color"
          args={[colorArray, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={1.5}
        vertexColors
        sizeAttenuation
        transparent
        opacity={0.85}
        depthWrite={false}
      />
    </points>
  )
}
