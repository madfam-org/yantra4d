import { forwardRef, useImperativeHandle } from 'react'
import { useThree } from '@react-three/fiber'

const SceneController = forwardRef(({ cameraViews = [] }, ref) => {
  const { gl, camera, scene } = useThree()

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
      camera.updateProjectionMatrix()
    }
  }))
  return null
})

SceneController.displayName = "SceneController"

export default SceneController
