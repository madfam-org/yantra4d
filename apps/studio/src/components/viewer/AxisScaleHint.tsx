import { useMemo } from 'react'
import * as THREE from 'three'
import { Line, Html, Cone } from '@react-three/drei'

const AMBER = '#f59e0b'
const ARROW_TIP_HEIGHT = 3
const ARROW_TIP_RADIUS = 1.5
const PADDING = 5

interface ParamDef {
  min?: number
  max?: number
}

interface PreviewHint {
  type: string
  axis: string
  scale_factor?: number
  affected_parts?: string[]
}

interface HoveredParam {
  paramId: string
  paramDef: ParamDef
  hint: PreviewHint
  currentValue?: number
}

interface ArrowTipProps {
  position: number[]
  axisIndex: number
  flip: boolean
}

function ArrowTip({ position, axisIndex, flip }: ArrowTipProps) {
  // Orient the cone along the axis direction
  const rotation = useMemo(() => {
    const r = [0, 0, 0]
    if (axisIndex === 0) r[2] = flip ? Math.PI / 2 : -Math.PI / 2
    else if (axisIndex === 1) r[0] = flip ? -Math.PI / 2 : Math.PI / 2
    else r[0] = flip ? Math.PI : 0
    return r
  }, [axisIndex, flip])

  return (
    <mesh position={position as [number, number, number]} rotation={rotation as [number, number, number]}>
      <coneGeometry args={[ARROW_TIP_RADIUS, ARROW_TIP_HEIGHT, 8]} />
      <meshBasicMaterial color={AMBER} transparent opacity={0.7} />
    </mesh>
  )
}

interface RangeLabelProps {
  value: number | string | undefined
}

function RangeLabel({ value }: RangeLabelProps) {
  return (
    <div
      className="bg-background/80 text-amber-500 text-xs px-1.5 py-0.5 rounded shadow-sm border border-amber-500/30 backdrop-blur-sm whitespace-nowrap font-mono"
      aria-hidden="true"
    >
      {typeof value === 'number' ? value.toFixed(value % 1 === 0 ? 0 : 1) : value}
    </div>
  )
}

interface RadialScaleHintProps {
  param: HoveredParam
  bbox: THREE.Box3 | null
  centerOfMass: number[] | null
}

function RadialScaleHint({ param, bbox, centerOfMass }: RadialScaleHintProps) {
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
  const makeCircle = (radius: number, segments: number = 48): number[][] => {
    const pts: number[][] = []
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
      <Line points={makeCircle(minRadius) as [number, number, number][]} color={AMBER} lineWidth={1.5} dashed dashSize={2} gapSize={1.5} />
      <Line points={makeCircle(maxRadius) as [number, number, number][]} color={AMBER} lineWidth={1.5} dashed dashSize={2} gapSize={1.5} />
      <Html position={[center[0] + minRadius, center[1], center[2]] as [number, number, number]} center className="pointer-events-none select-none">
        <RangeLabel value={paramDef.min} />
      </Html>
      <Html position={[center[0] + maxRadius, center[1], center[2]] as [number, number, number]} center className="pointer-events-none select-none">
        <RangeLabel value={paramDef.max} />
      </Html>
    </group>
  )
}

interface AxisScaleHintProps {
  param: HoveredParam
  bbox: THREE.Box3 | null
  centerOfMass: number[] | null
}

export default function AxisScaleHint({ param, bbox, centerOfMass }: AxisScaleHintProps) {
  const { paramDef, hint } = param
  const axisIndex = ({ x: 0, y: 1, z: 2 } as Record<string, number>)[hint.axis]

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

  const center: number[] = centerOfMass ? [...centerOfMass] : [0, 0, 0]
  const startPos: number[] = [...center]
  startPos[axisIndex] = minExtent - PADDING
  const endPos: number[] = [...center]
  endPos[axisIndex] = maxExtent + PADDING

  return (
    <group aria-hidden="true">
      <Line
        points={[startPos as [number, number, number], endPos as [number, number, number]]}
        color={AMBER}
        lineWidth={2}
        dashed
        dashSize={3}
        gapSize={2}
      />
      <ArrowTip position={startPos} axisIndex={axisIndex} flip />
      <ArrowTip position={endPos} axisIndex={axisIndex} flip={false} />
      <Html position={startPos as [number, number, number]} center className="pointer-events-none select-none">
        <RangeLabel value={paramDef.min} />
      </Html>
      <Html position={endPos as [number, number, number]} center className="pointer-events-none select-none">
        <RangeLabel value={paramDef.max} />
      </Html>
    </group>
  )
}
