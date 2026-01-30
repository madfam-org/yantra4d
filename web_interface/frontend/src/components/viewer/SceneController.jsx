import { forwardRef, useImperativeHandle } from 'react'
import { useThree } from '@react-three/fiber'

const SceneController = forwardRef((props, ref) => {
  const { gl, camera, scene } = useThree()

  useImperativeHandle(ref, () => ({
    captureSnapshot: () => {
      gl.render(scene, camera)
      return gl.domElement.toDataURL('image/png')
    },
    setCameraView: (view) => {
      const dist = 100
      camera.up.set(0, 0, 1)
      switch (view) {
        case 'iso':
          camera.position.set(50, 50, 50)
          break
        case 'top':
          camera.position.set(0, 0, dist)
          break
        case 'front':
          camera.position.set(0, -dist, 0)
          break
        case 'right':
          camera.position.set(dist, 0, 0)
          break
      }
      camera.lookAt(0, 0, 0)
      camera.updateProjectionMatrix()
    }
  }))
  return null
})

SceneController.displayName = "SceneController"

export default SceneController
