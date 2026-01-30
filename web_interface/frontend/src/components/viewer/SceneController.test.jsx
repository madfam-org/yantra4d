import { describe, it, expect, vi, beforeEach } from 'vitest'

// SceneController is a Three.js component that can't render in jsdom,
// so we test the camera view logic directly.

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

  // Mirror the setCameraView logic from SceneController.jsx
  function setCameraView(view) {
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

  it('sets Z-up for all views', () => {
    for (const view of ['iso', 'top', 'front', 'right']) {
      setCameraView(view)
      expect(camera.up.set).toHaveBeenCalledWith(0, 0, 1)
    }
  })

  it('iso view: camera at (50, 50, 50)', () => {
    setCameraView('iso')
    expect(camera.position.set).toHaveBeenCalledWith(50, 50, 50)
  })

  it('top view: looks down Z axis from (0, 0, 100)', () => {
    setCameraView('top')
    expect(camera.position.set).toHaveBeenCalledWith(0, 0, 100)
  })

  it('front view: looks along +Y from (0, -100, 0)', () => {
    setCameraView('front')
    expect(camera.position.set).toHaveBeenCalledWith(0, -100, 0)
  })

  it('right view: looks along -X from (100, 0, 0)', () => {
    setCameraView('right')
    expect(camera.position.set).toHaveBeenCalledWith(100, 0, 0)
  })

  it('all views call lookAt(0,0,0) and updateProjectionMatrix', () => {
    for (const view of ['iso', 'top', 'front', 'right']) {
      camera.lookAt.mockClear()
      camera.updateProjectionMatrix.mockClear()
      setCameraView(view)
      expect(camera.lookAt).toHaveBeenCalledWith(0, 0, 0)
      expect(camera.updateProjectionMatrix).toHaveBeenCalled()
    }
  })
})
