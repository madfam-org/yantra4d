import { useMemo } from 'react'
import { Line, Html, Cone } from '@react-three/drei'

const AMBER = '#f59e0b'
const ARROW_TIP_HEIGHT = 3
const ARROW_TIP_RADIUS = 1.5
const PADDING = 5

function ArrowTip({ position, axisIndex, flip }) {
  // Orient the cone along the axis direction
  const rotation = useMemo(() => {
    const r = [0, 0, 0]
    if (axisIndex === 0) r[2] = flip ? Math.PI / 2 : -Math.PI / 2
    else if (axisIndex === 1) r[0] = flip ? -Math.PI / 2 : Math.PI / 2
    else r[0] = flip ? Math.PI : 0
    return r
  }, [axisIndex, flip])

  return (
    <mesh position={position} rotation={rotation}>
      <coneGeometry args={[ARROW_TIP_RADIUS, ARROW_TIP_HEIGHT, 8]} />
      <meshBasicMaterial color={AMBER} transparent opacity={0.7} />
    </mesh>
  )
}

function RangeLabel({ value }) {
  return (
    <div
      className="bg-background/80 text-amber-500 text-xs px-1.5 py-0.5 rounded shadow-sm border border-amber-500/30 backdrop-blur-sm whitespace-nowrap font-mono"
      aria-hidden="true"
    >
      {typeof value === 'number' ? value.toFixed(value % 1 === 0 ? 0 : 1) : value}
    </div>
  )
}

function RadialScaleHint({ param, bbox, centerOfMass }) {
  if (!bbox) return null
  const { paramDef } = param
  const center = centerOfMass || [0, 0, 0]

  // Show a ring in XY plane at the center
  const currentRadius = Math.max(
    (bbox.max.x - bbox.min.x) / 2,
    (bbox.max.y - bbox.min.y) / 2
  )
  const scaleFactor = currentRadius / Math.max(param.currentValue || 1, 0.001)
  const minRadius = Math.max((paramDef.min || 0) * scaleFactor, 0.5)
  const maxRadius = (paramDef.max || paramDef.min || 1) * scaleFactor

  // Generate circle points for min and max radii
  const makeCircle = (radius, segments = 48) => {
    const pts = []
    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * Math.PI * 2
      pts.push([
        center[0] + Math.cos(angle) * radius,
        center[1] + Math.sin(angle) * radius,
        center[2],
      ])
    }
    return pts
  }

  return (
    <group aria-hidden="true">
      <Line points={makeCircle(minRadius)} color={AMBER} lineWidth={1.5} dashed dashSize={2} gapSize={1.5} />
      <Line points={makeCircle(maxRadius)} color={AMBER} lineWidth={1.5} dashed dashSize={2} gapSize={1.5} />
      <Html position={[center[0] + minRadius, center[1], center[2]]} center className="pointer-events-none select-none">
        <RangeLabel value={paramDef.min} />
      </Html>
      <Html position={[center[0] + maxRadius, center[1], center[2]]} center className="pointer-events-none select-none">
        <RangeLabel value={paramDef.max} />
      </Html>
    </group>
  )
}

export default function AxisScaleHint({ param, bbox, centerOfMass }) {
  const { paramDef, hint } = param
  const axisIndex = { x: 0, y: 1, z: 2 }[hint.axis]

  if (axisIndex == null) {
    if (hint.axis === 'radial') {
      return <RadialScaleHint param={param} bbox={bbox} centerOfMass={centerOfMass} />
    }
    return null
  }

  if (!bbox) return null

  const bboxMin = bbox.min.toArray()
  const bboxMax = bbox.max.toArray()
  const bboxSize = bboxMax[axisIndex] - bboxMin[axisIndex]
  const range = Math.max((paramDef.max || 0) - (paramDef.min || 0), 1)
  const scaleFactor = hint.scale_factor || (bboxSize / range)
  const minExtent = bboxMin[axisIndex] - ((param.currentValue || 0) - (paramDef.min || 0)) * scaleFactor
  const maxExtent = bboxMax[axisIndex] + ((paramDef.max || 0) - (param.currentValue || 0)) * scaleFactor

  const center = centerOfMass ? [...centerOfMass] : [0, 0, 0]
  const startPos = [...center]
  startPos[axisIndex] = minExtent - PADDING
  const endPos = [...center]
  endPos[axisIndex] = maxExtent + PADDING

  return (
    <group aria-hidden="true">
      <Line
        points={[startPos, endPos]}
        color={AMBER}
        lineWidth={2}
        dashed
        dashSize={3}
        gapSize={2}
      />
      <ArrowTip position={startPos} axisIndex={axisIndex} flip />
      <ArrowTip position={endPos} axisIndex={axisIndex} flip={false} />
      <Html position={startPos} center className="pointer-events-none select-none">
        <RangeLabel value={paramDef.min} />
      </Html>
      <Html position={endPos} center className="pointer-events-none select-none">
        <RangeLabel value={paramDef.max} />
      </Html>
    </group>
  )
}
