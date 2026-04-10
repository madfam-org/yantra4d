import { useRef, useMemo } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { useWorkerLoader } from '../../hooks/render/useWorkerLoader'

interface GhostModelProps {
  url: string
  isGlb: boolean
  color: string
}

function GhostModel({ url, isGlb, color }: GhostModelProps) {
  const { geometry } = useWorkerLoader(url, isGlb)

  if (!geometry) return null

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        color={color}
        transparent
        opacity={0.12}
        depthWrite={false}
        roughness={0.5}
        metalness={0.1}
      />
    </mesh>
  )
}

const BREATHING_SPEED = Math.PI // 0.5Hz cycle
const OPACITY_MIN = 0.08
const OPACITY_MAX = 0.16
const STATIC_OPACITY = 0.12

/**
 * R3F component that renders cached min/max geometry as semi-transparent
 * purple ghost meshes with a subtle breathing animation.
 *
 * @param {{ variants: { min?: Array, max?: Array }, color?: string }} props
 */
interface GhostPart {
  url: string
  isGlb: boolean
  type: string
  bound?: string
}

export interface GhostVariants {
  min?: GhostPart[]
  max?: GhostPart[]
}

export interface GhostGeometryOverlayProps {
  variants: GhostVariants
  color?: string
}

export default function GhostGeometryOverlay({ variants, color = '#a855f7' }: GhostGeometryOverlayProps) {
  const groupRef = useRef<THREE.Group>(null)
  const reducedMotion = useMemo(
    () => window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false,
    []
  )

  useFrame(({ clock }) => {
    if (!groupRef.current || reducedMotion) return
    const t = Math.sin(clock.getElapsedTime() * BREATHING_SPEED) * 0.5 + 0.5
    const opacity = OPACITY_MIN + t * (OPACITY_MAX - OPACITY_MIN)
    groupRef.current.traverse(child => {
      const mesh = child as THREE.Mesh
      if (mesh.material && (mesh.material as THREE.MeshStandardMaterial).opacity !== undefined) {
        (mesh.material as THREE.MeshStandardMaterial).opacity = opacity
      }
    })
  })

  const allParts = useMemo(() => {
    const result: GhostPart[] = []
    if (variants?.min) result.push(...variants.min.map(p => ({ ...p, bound: 'min' })))
    if (variants?.max) result.push(...variants.max.map(p => ({ ...p, bound: 'max' })))
    return result
  }, [variants])

  if (!allParts.length) return null

  return (
    <group ref={groupRef} aria-hidden="true">
      {allParts.map((part, i) => (
        <GhostModel
          key={`ghost-${part.bound}-${part.type}-${i}`}
          url={part.url}
          isGlb={part.isGlb}
          color={color}
        />
      ))}
    </group>
  )
}
