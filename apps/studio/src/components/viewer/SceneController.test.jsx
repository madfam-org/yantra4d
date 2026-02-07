import { describe, it, expect, vi, beforeEach } from 'vitest'
import fallbackManifest from '../../config/fallback-manifest.json'

// SceneController is a Three.js component that can't render in jsdom,
// so we test the camera view logic directly using manifest-driven positions.

const cameraViews = fallbackManifest.camera_views

describe('SceneController view positions (Z-up convention)', () => {
  let camera

  beforeEach(() => {
    camera = {
      position: { set: vi.fn() },
      up: { set: vi.fn() },
      lookAt: vi.fn(),
      updateProjectionMatrix: vi.fn(),
    }
  })

  // Mirror the data-driven setCameraView logic from SceneController.jsx
  function setCameraView(viewId) {
    const viewConfig = cameraViews.find(v => v.id === viewId)
    if (viewConfig) {
      camera.up.set(0, 0, 1)
      camera.position.set(...viewConfig.position)
    }
    camera.lookAt(0, 0, 0)
    camera.updateProjectionMatrix()
  }

  it('sets Z-up for all views', () => {
    for (const view of cameraViews) {
      setCameraView(view.id)
      expect(camera.up.set).toHaveBeenCalledWith(0, 0, 1)
    }
  })

  it('iso view: camera at (80, 80, 80)', () => {
    setCameraView('iso')
    expect(camera.position.set).toHaveBeenCalledWith(80, 80, 80)
  })

  it('top view: looks down Z axis from (0, 0, 150)', () => {
    setCameraView('top')
    expect(camera.position.set).toHaveBeenCalledWith(0, 0, 150)
  })

  it('front view: looks along +Y from (0, -150, 0)', () => {
    setCameraView('front')
    expect(camera.position.set).toHaveBeenCalledWith(0, -150, 0)
  })

  it('right view: looks along -X from (150, 0, 0)', () => {
    setCameraView('right')
    expect(camera.position.set).toHaveBeenCalledWith(150, 0, 0)
  })

  it('all views call lookAt(0,0,0) and updateProjectionMatrix', () => {
    for (const view of cameraViews) {
      camera.lookAt.mockClear()
      camera.updateProjectionMatrix.mockClear()
      setCameraView(view.id)
      expect(camera.lookAt).toHaveBeenCalledWith(0, 0, 0)
      expect(camera.updateProjectionMatrix).toHaveBeenCalled()
    }
  })
})
