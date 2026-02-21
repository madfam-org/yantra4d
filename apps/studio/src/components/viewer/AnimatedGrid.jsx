import React, { useRef, useState, useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { Edges } from '@react-three/drei'
import { fetchAssemblyGeometries } from '../../services/domain/assemblyFetcher'
import { useManifest } from '../../contexts/ManifestProvider'

function getCombinedCenter(geometries) {
  const box = new THREE.Box3()
  for (const { geometry } of geometries) {
    geometry.computeBoundingBox()
    box.union(geometry.boundingBox)
  }
  const center = new THREE.Vector3()
  box.getCenter(center)
  return center
}

const ROTATION_SPEED = Math.PI / 2 // π/2 rad/s → 1 full 90° turn per second
const PAUSE_DURATION = 0.3 // seconds between rotations

function AnimatedGrid({ params, colors, wireframe, onReady }) {
  const { getViewerConfig, manifest } = useManifest()
  const rows = params.rows
  const cols = params.cols
  const size = params.size
  const rotationClearance = params.rotation_clearance
  const tubingH = params.tubing_H ?? 0
  // Grid pitch formula: pitch = size * sqrt(2) + rotation_clearance
  const gridPitch = size * Math.SQRT2 + rotationClearance
  const defaultColor = getViewerConfig().default_color || '#e5e7eb'

  const [geometries, setGeometries] = useState(null)
  const [geoCenter, setGeoCenter] = useState(null)
  const [error, setError] = useState(null)

  // Per-cube animation state: { currentAngle, targetAngle }
  const cubeCount = rows * cols
  const animState = useRef(null)
  const pauseTimer = useRef(0)

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
    fetchAssemblyGeometries(params, geometryKeys)
      .then(geos => {
        if (!cancelled) {
          setGeometries(geos)
          setGeoCenter(getCombinedCenter(geos))
          onReady?.()
        }
      })
      .catch(err => { if (!cancelled) setError(err.message) })
    return () => { cancelled = true }
  }, [geoHash]) // eslint-disable-line react-hooks/exhaustive-deps

  // Group refs created synchronously so they're available on first render
  const groupRefs = useMemo(
    () => Array.from({ length: cubeCount }, () => React.createRef()),
    [cubeCount]
  )

  // Animation loop
  useFrame((_, delta) => {
    if (!animState.current || !geometries) return

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
