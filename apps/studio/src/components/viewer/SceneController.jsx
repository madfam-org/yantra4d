import { forwardRef, useImperativeHandle, useRef } from 'react'
import { useThree, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const SceneController = forwardRef(({ cameraViews = [] }, ref) => {
  const { gl, camera, scene } = useThree()
  const animationRef = useRef(null)

  // Grab OrbitControls from the default controls
  const { controls } = useThree()

  useFrame((_, delta) => {
    const anim = animationRef.current
    if (!anim) return

    anim.elapsed += delta
    const t = Math.min(anim.elapsed / anim.duration, 1)
    // Smooth ease-in-out
    const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2

    camera.position.lerpVectors(anim.startPos, anim.endPos, ease)

    if (controls?.target) {
      const target = new THREE.Vector3().lerpVectors(anim.startTarget, anim.endTarget, ease)
      controls.target.copy(target)
      controls.update()
    } else {
      const target = new THREE.Vector3().lerpVectors(anim.startTarget, anim.endTarget, ease)
      camera.lookAt(target)
    }

    camera.updateProjectionMatrix()

    if (t >= 1) {
      animationRef.current = null
    }
  })

  useImperativeHandle(ref, () => ({
    captureSnapshot: () => {
      gl.render(scene, camera)
      return gl.domElement.toDataURL('image/png')
    },
    setCameraView: (viewId) => {
      const viewConfig = cameraViews.find(v => v.id === viewId)
      if (viewConfig) {
        camera.up.set(0, 0, 1)
        camera.position.set(...viewConfig.position)
      }
      camera.lookAt(0, 0, 0)
      if (controls?.target) {
        controls.target.set(0, 0, 0)
        controls.update()
      }
      camera.updateProjectionMatrix()
    },
    animateTo: (position, target, duration = 0.5) => {
      const currentTarget = controls?.target
        ? controls.target.clone()
        : new THREE.Vector3(0, 0, 0)

      animationRef.current = {
        startPos: camera.position.clone(),
        endPos: new THREE.Vector3(...position),
        startTarget: currentTarget,
        endTarget: new THREE.Vector3(...(target || [0, 0, 0])),
        elapsed: 0,
        duration,
      }
    },
    getCameraState: () => ({
      position: camera.position.toArray(),
      target: controls?.target ? controls.target.toArray() : [0, 0, 0],
    }),
  }))
  return null
})

SceneController.displayName = "SceneController"

export default SceneController
