import { useMemo } from 'react'
import { Color } from 'three'

/**
 * ThicknessOverlay — visualizes wall thickness as a colored point cloud.
 * Maps thickness values to a red→yellow→green color ramp.
 *
 * Red (<0.8mm) → Yellow (0.8-1.2mm) → Green (>1.2mm)
 * Thresholds can be adjusted per material.
 *
 * @param {Array} points - [[x,y,z], ...] sample points
 * @param {Array} thicknesses - [number, ...] thickness at each point
 * @param {number} thinThreshold - below this = red (default 0.8)
 * @param {number} okThreshold - above this = green (default 1.2)
 */
export default function ThicknessOverlay({
  points = [],
  thicknesses = [],
  thinThreshold = 0.8,
  okThreshold = 1.2,
}) {
  const { colorArray, positionArray } = useMemo(() => {
    if (!points.length || !thicknesses.length) {
      return { colorArray: new Float32Array(0), positionArray: new Float32Array(0) }
    }

    const positions = new Float32Array(points.length * 3)
    const colors = new Float32Array(points.length * 3)

    const red = new Color('#ef4444')
    const yellow = new Color('#eab308')
    const green = new Color('#22c55e')

    for (let i = 0; i < points.length; i++) {
      const p = points[i]
      positions[i * 3] = p[0]
      positions[i * 3 + 1] = p[1]
      positions[i * 3 + 2] = p[2]

      const t = thicknesses[i]
      let color
      if (t === Infinity || t === null || t === undefined) {
        color = green // unknown = assume OK
      } else if (t < thinThreshold) {
        color = red
      } else if (t < okThreshold) {
        // Interpolate red → yellow → green
        const frac = (t - thinThreshold) / (okThreshold - thinThreshold)
        color = frac < 0.5
          ? new Color().lerpColors(red, yellow, frac * 2)
          : new Color().lerpColors(yellow, green, (frac - 0.5) * 2)
      } else {
        color = green
      }

      colors[i * 3] = color.r
      colors[i * 3 + 1] = color.g
      colors[i * 3 + 2] = color.b
    }

    return { colorArray: colors, positionArray: positions }
  }, [points, thicknesses, thinThreshold, okThreshold])

  if (positionArray.length === 0) return null

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={positionArray.length / 3}
          array={positionArray}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-color"
          count={colorArray.length / 3}
          array={colorArray}
          itemSize={3}
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
