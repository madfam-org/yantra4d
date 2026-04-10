import React, { useRef, useState, useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { Edges } from '@react-three/drei'
import { fetchAssemblyGeometries } from '../../services/domain/assemblyFetcher'
import { useManifest } from '../../contexts/project/ManifestProvider'

interface AssemblyGeometry {
  type: string
  geometry: THREE.BufferGeometry
}

function getCombinedCenter(geometries: AssemblyGeometry[]): THREE.Vector3 {
  const box = new THREE.Box3()
  for (const { geometry } of geometries) {
    geometry.computeBoundingBox()
    box.union(geometry.boundingBox!)
  }
  const center = new THREE.Vector3()
  box.getCenter(center)
  return center
}

const ROTATION_SPEED = Math.PI / 2 // π/2 rad/s → 1 full 90° turn per second
const PAUSE_DURATION = 0.3 // seconds between rotations

interface AnimState {
  currentAngle: number
  targetAngle: number
}

interface AnimatedGridProps {
  params: Record<string, unknown>
  colors: Record<string, string>
  wireframe: boolean
  onReady?: () => void
  onError?: (message: string) => void
}

function AnimatedGrid({ params, colors, wireframe, onReady, onError }: AnimatedGridProps) {
  const { getViewerConfig, manifest, projectSlug } = useManifest()
  const rows = params.rows as number
  const cols = params.cols as number
  const size = params.size as number
  const rotationClearance = params.rotation_clearance as number
  const tubingH = (params.tubing_H as number) ?? 0
  // Grid pitch formula: pitch = size * sqrt(2) + rotation_clearance
  const gridPitch = size * Math.SQRT2 + rotationClearance
  const defaultColor = (getViewerConfig().default_color as string) || '#e5e7eb'

  const [geometries, setGeometries] = useState<AssemblyGeometry[] | null>(null)
  const [geoCenter, setGeoCenter] = useState<THREE.Vector3 | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Per-cube animation state: { currentAngle, targetAngle }
  const cubeCount = (rows as number) * (cols as number)
  const animState = useRef<AnimState[] | null>(null)
  const pauseTimer = useRef<number>(0)

  // Initialize/reset animation state when grid size changes
  useEffect(() => {
    const count = rows * cols
    animState.current = Array.from({ length: count }, () => ({
      currentAngle: 0,
      targetAngle: 0,
    }))
    pauseTimer.current = 0
  }, [rows, cols])

  // Derive geometry-affecting parameter keys from manifest (exclude checkboxes)
  const geometryKeys = useMemo(
    () => manifest.parameters.filter(p => p.type !== 'checkbox').map(p => p.id),
    [manifest.parameters]
  )

  // Stable hash of geometry-affecting params for dependency tracking
  const geoHash = useMemo(
    () => JSON.stringify(geometryKeys.map(k => params[k])),
    [geometryKeys, params]
  )

  // Fetch assembly geometries on mount / param change
  useEffect(() => {
    let cancelled = false
    setError(null) // eslint-disable-line react-hooks/set-state-in-effect
    fetchAssemblyGeometries(params, geometryKeys, projectSlug)
      .then(geos => {
        if (!cancelled) {
          setGeometries(geos)
          setGeoCenter(getCombinedCenter(geos))
          onReady?.()
        }
      })
      .catch(err => { if (!cancelled) { setError(err.message); onError?.(err.message) } })
    return () => { cancelled = true }
  }, [geoHash]) // eslint-disable-line react-hooks/exhaustive-deps

  // Group refs created synchronously so they're available on first render
  const groupRefs = useMemo(
    () => Array.from({ length: cubeCount }, () => React.createRef<THREE.Group>()),
    [cubeCount]
  )

  // Cache reduced motion preference (avoids per-frame matchMedia calls)
  const prefersReducedMotion = useRef(
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )

  // Animation loop — skipped entirely when user prefers reduced motion
  useFrame((_, delta) => {
    if (!animState.current || !geometries || prefersReducedMotion.current) return

    const state = animState.current
    const animatingIdx = state.findIndex(s => Math.abs(s.currentAngle - s.targetAngle) > 0.001)

    if (animatingIdx >= 0) {
      // Lerp toward target
      const s = state[animatingIdx]
      const diff = s.targetAngle - s.currentAngle
      const step = Math.sign(diff) * Math.min(Math.abs(diff), ROTATION_SPEED * delta)
      s.currentAngle += step

      // Snap when close
      if (Math.abs(s.targetAngle - s.currentAngle) < 0.01) {
        s.currentAngle = s.targetAngle
      }

      // Apply rotation
      const ref = groupRefs[animatingIdx]
      if (ref?.current) {
        ref.current.rotation.z = s.currentAngle
      }
    } else {
      // No cube animating — wait, then pick a random one
      pauseTimer.current += delta
      if (pauseTimer.current >= PAUSE_DURATION) {
        pauseTimer.current = 0
        const idx = Math.floor(Math.random() * cubeCount)
        state[idx].targetAngle += Math.PI / 2
      }
    }
  })

  if (error || !geometries || !geoCenter) return null

  const cx = geoCenter.x
  const cy = geoCenter.y
  const cz = geoCenter.z

  // Build grid of cubes
  const cubes = []
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c
      const yPos = c * gridPitch    // columns spread along Y
      const zPos = r * (size + tubingH) + tubingH  // rows stack along Z with tubing spacers
      cubes.push(
        <group key={idx} position={[cx, yPos + cy, zPos + cz]}>
          <group ref={groupRefs[idx]}>
          <group position={[-cx, -cy, -cz]}>
            {geometries.map(({ type, geometry }) => (
              <mesh key={type} geometry={geometry.clone()}>
                <meshStandardMaterial
                  key={wireframe ? 'wf' : 'solid'}
                  color={colors[type] || defaultColor}
                  roughness={0.5}
                  metalness={0.1}
                  transparent={wireframe}
                  opacity={wireframe ? 0.08 : 1}
                />
                <Edges threshold={15} color="#374151" />
              </mesh>
            ))}
          </group>
          </group>
        </group>
      )
    }
  }

  return <group>{cubes}</group>
}

export default AnimatedGrid
