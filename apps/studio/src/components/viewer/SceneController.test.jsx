import React, { createRef } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'

// Capture useFrame callback
let frameCallback = null

// Simple Vector3 mock — needs to be available before vi.mock hoisting
const makeVec = (x = 0, y = 0, z = 0) => ({
  x, y, z,
  lerpVectors: vi.fn().mockReturnThis(),
  copy: vi.fn().mockReturnThis(),
  set: vi.fn().mockReturnThis(),
  clone: vi.fn(function() { return makeVec(this.x, this.y, this.z) }),
  toArray: vi.fn(function() { return [this.x, this.y, this.z] }),
})

const mockCamera = {
  position: { ...makeVec(), set: vi.fn(), clone: vi.fn(() => makeVec()), lerpVectors: vi.fn(), toArray: vi.fn(() => [10, 20, 30]) },
  up: { set: vi.fn() },
  lookAt: vi.fn(),
  updateProjectionMatrix: vi.fn(),
}
const mockTarget = { ...makeVec(), set: vi.fn(), copy: vi.fn(), clone: vi.fn(() => makeVec()), toArray: vi.fn(() => [0, 0, 0]) }
const mockControls = { target: mockTarget, update: vi.fn() }
const mockGl = { render: vi.fn(), domElement: { toDataURL: vi.fn(() => 'data:image/png;base64,mock') } }
const mockScene = {}

vi.mock('@react-three/fiber', () => ({
  useThree: vi.fn(() => ({
    gl: mockGl,
    camera: mockCamera,
    scene: mockScene,
    controls: mockControls,
  })),
  useFrame: vi.fn((cb) => { frameCallback = cb }),
}))

vi.mock('three', () => {
  function Vector3(x = 0, y = 0, z = 0) {
    this.x = x; this.y = y; this.z = z
  }
  Vector3.prototype.lerpVectors = function() { return this }
  Vector3.prototype.copy = function(v) { this.x = v.x; this.y = v.y; this.z = v.z; return this }
  Vector3.prototype.set = function(x, y, z) { this.x = x; this.y = y; this.z = z; return this }
  Vector3.prototype.clone = function() { return new Vector3(this.x, this.y, this.z) }
  Vector3.prototype.toArray = function() { return [this.x, this.y, this.z] }
  return { Vector3 }
})

import SceneController from './SceneController'

beforeEach(() => {
  vi.clearAllMocks()
  frameCallback = null
})

describe('SceneController', () => {
  it('renders null (no visible DOM)', () => {
    const ref = createRef()
    const { container } = render(<SceneController ref={ref} cameraViews={[]} />)
    expect(container.innerHTML).toBe('')
  })

  it('exposes captureSnapshot via ref', () => {
    const ref = createRef()
    render(<SceneController ref={ref} cameraViews={[]} />)
    const result = ref.current.captureSnapshot()
    expect(mockGl.render).toHaveBeenCalledWith(mockScene, mockCamera)
    expect(result).toBe('data:image/png;base64,mock')
  })

  it('setCameraView sets camera position from matching view', () => {
    const ref = createRef()
    const views = [{ id: 'top', position: [0, 0, 150] }]
    render(<SceneController ref={ref} cameraViews={views} />)
    ref.current.setCameraView('top')
    expect(mockCamera.up.set).toHaveBeenCalledWith(0, 0, 1)
    expect(mockCamera.position.set).toHaveBeenCalledWith(0, 0, 150)
    expect(mockCamera.lookAt).toHaveBeenCalledWith(0, 0, 0)
    expect(mockCamera.updateProjectionMatrix).toHaveBeenCalled()
  })

  it('setCameraView with unknown id still calls lookAt', () => {
    const ref = createRef()
    render(<SceneController ref={ref} cameraViews={[]} />)
    ref.current.setCameraView('nonexistent')
    expect(mockCamera.lookAt).toHaveBeenCalledWith(0, 0, 0)
    expect(mockCamera.updateProjectionMatrix).toHaveBeenCalled()
  })

  it('getCameraState returns position and target', () => {
    const ref = createRef()
    render(<SceneController ref={ref} cameraViews={[]} />)
    const state = ref.current.getCameraState()
    expect(state.position).toEqual([10, 20, 30])
    expect(state.target).toEqual([0, 0, 0])
  })

  it('animateTo sets animation state processed by useFrame', () => {
    const ref = createRef()
    render(<SceneController ref={ref} cameraViews={[]} />)
    ref.current.animateTo([50, 50, 50], [0, 0, 0], 1.0)
    expect(frameCallback).toBeTruthy()
    // Process one frame
    frameCallback(null, 0.5)
    expect(mockCamera.updateProjectionMatrix).toHaveBeenCalled()
  })

  it('useFrame callback with no animation does nothing', () => {
    const ref = createRef()
    render(<SceneController ref={ref} cameraViews={[]} />)
    frameCallback(null, 0.016)
    expect(mockCamera.updateProjectionMatrix).not.toHaveBeenCalled()
  })

  it('animation completes when elapsed >= duration', () => {
    const ref = createRef()
    render(<SceneController ref={ref} cameraViews={[]} />)
    ref.current.animateTo([100, 0, 0], [0, 0, 0], 0.1)
    // Large delta to complete animation
    frameCallback(null, 1.0)
    expect(mockCamera.updateProjectionMatrix).toHaveBeenCalled()
    // After completion, another frame should be a no-op
    mockCamera.updateProjectionMatrix.mockClear()
    frameCallback(null, 0.016)
    expect(mockCamera.updateProjectionMatrix).not.toHaveBeenCalled()
  })

  it('animateTo without target defaults to origin', () => {
    const ref = createRef()
    render(<SceneController ref={ref} cameraViews={[]} />)
    // null target should default to [0,0,0]
    ref.current.animateTo([50, 50, 50], null, 0.5)
    frameCallback(null, 0.25)
    expect(mockCamera.updateProjectionMatrix).toHaveBeenCalled()
  })
})
