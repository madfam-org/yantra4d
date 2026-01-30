import React, { useRef, useState, useEffect, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { Edges } from '@react-three/drei'
import { fetchAssemblyGeometries } from '../../services/assemblyFetcher'

const ROTATION_SPEED = 4.0 // radians per second (π/2 in ~0.4s)
const PAUSE_DURATION = 0.3 // seconds between rotations

function AnimatedGrid({ params, colors, wireframe, onReady }) {
  const rows = params.rows || 2
  const cols = params.cols || 2
  const size = params.size || 20
  const gridPitch = params.grid_pitch || size
  const defaultColor = '#e5e7eb'

  const [geometries, setGeometries] = useState(null)
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

  // Fetch assembly geometries on mount / param change
  useEffect(() => {
    let cancelled = false
    setError(null) // eslint-disable-line react-hooks/set-state-in-effect
    fetchAssemblyGeometries(params)
      .then(geos => {
        if (!cancelled) {
          setGeometries(geos)
          onReady?.()
        }
      })
      .catch(err => { if (!cancelled) setError(err.message) })
    return () => { cancelled = true }
  }, [params.size, params.thick, params.rod_D, params.clearance, params.fit_clear,
      params.letter_depth, params.letter_size, params.rod_extension, params.rotation_clearance,
      params.letter_bottom, params.letter_top])

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

  if (error || !geometries) return null

  // Build grid of cubes
  const cubes = []
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c
      const x = c * gridPitch
      const y = r * gridPitch
      cubes.push(
        <group key={idx} position={[x + size / 2, y + size / 2, 0]}>
          <group ref={groupRefs[idx]}>
          <group position={[-size / 2, -size / 2, 0]}>
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
