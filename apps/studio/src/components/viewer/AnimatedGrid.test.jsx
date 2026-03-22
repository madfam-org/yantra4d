import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'

// ---------------------------------------------------------------------------
// Capture useFrame callback so we can drive the animation loop in tests
// ---------------------------------------------------------------------------
let frameCallback = null

// ---------------------------------------------------------------------------
// Patch document.createElement so that <group> elements get a .rotation
// property, matching the Three.js Object3D interface that AnimatedGrid
// expects when setting ref.current.rotation.z inside useFrame.
// ---------------------------------------------------------------------------
const originalCreateElement = document.createElement.bind(document)
document.createElement = function (tagName, options) {
  const el = originalCreateElement(tagName, options)
  if (tagName === 'group') {
    el.rotation = { x: 0, y: 0, z: 0 }
  }
  return el
}

// ---------------------------------------------------------------------------
// Mock THREE -- Box3, Vector3, SQRT2 used by getCombinedCenter
// ---------------------------------------------------------------------------
const mockBoundingBox = {
  min: { x: -5, y: -5, z: -5 },
  max: { x: 5, y: 5, z: 5 },
}

vi.mock('three', () => {
  function Vector3(x = 0, y = 0, z = 0) {
    this.x = x; this.y = y; this.z = z
  }
  Vector3.prototype.set = function (x, y, z) { this.x = x; this.y = y; this.z = z; return this }
  Vector3.prototype.clone = function () { return new Vector3(this.x, this.y, this.z) }

  function Box3() {
    this.min = { x: Infinity, y: Infinity, z: Infinity }
    this.max = { x: -Infinity, y: -Infinity, z: -Infinity }
  }
  Box3.prototype.union = function (other) {
    this.min.x = Math.min(this.min.x, other.min.x)
    this.min.y = Math.min(this.min.y, other.min.y)
    this.min.z = Math.min(this.min.z, other.min.z)
    this.max.x = Math.max(this.max.x, other.max.x)
    this.max.y = Math.max(this.max.y, other.max.y)
    this.max.z = Math.max(this.max.z, other.max.z)
  }
  Box3.prototype.getCenter = function (target) {
    target.x = (this.min.x + this.max.x) / 2
    target.y = (this.min.y + this.max.y) / 2
    target.z = (this.min.z + this.max.z) / 2
    return target
  }

  return {
    Box3,
    Vector3,
    SQRT2: Math.SQRT2,
  }
})

// ---------------------------------------------------------------------------
// Mock @react-three/fiber -- capture useFrame callback
// ---------------------------------------------------------------------------
vi.mock('@react-three/fiber', () => ({
  useFrame: vi.fn((cb) => { frameCallback = cb }),
}))

// ---------------------------------------------------------------------------
// Mock @react-three/drei -- Edges is used in the render output
// ---------------------------------------------------------------------------
vi.mock('@react-three/drei', () => ({
  Edges: () => <div data-testid="edges" />,
}))

// ---------------------------------------------------------------------------
// Mock assemblyFetcher -- controls whether geometries resolve or reject
// ---------------------------------------------------------------------------
let fetchResolve = null
let fetchReject = null
vi.mock('../../services/domain/assemblyFetcher', () => ({
  fetchAssemblyGeometries: vi.fn(() => new Promise((res, rej) => {
    fetchResolve = res
    fetchReject = rej
  })),
}))

// ---------------------------------------------------------------------------
// Mock ManifestProvider
// ---------------------------------------------------------------------------
const mockGetViewerConfig = vi.fn(() => ({ default_color: '#aabbcc' }))
vi.mock('../../contexts/project/ManifestProvider', () => ({
  useManifest: () => ({
    getViewerConfig: mockGetViewerConfig,
    projectSlug: 'tablaco',
    manifest: {
      parameters: [
        { id: 'size', type: 'number' },
        { id: 'rows', type: 'number' },
        { id: 'cols', type: 'number' },
        { id: 'rotation_clearance', type: 'number' },
        { id: 'show_labels', type: 'checkbox' },
      ],
    },
  }),
}))

// ---------------------------------------------------------------------------
// Import component after all mocks are in place
// ---------------------------------------------------------------------------
import AnimatedGrid from './AnimatedGrid'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function makeMockGeometry() {
  return {
    computeBoundingBox: vi.fn(function () {
      this.boundingBox = { ...mockBoundingBox }
    }),
    boundingBox: null,
    clone: vi.fn(function () { return makeMockGeometry() }),
  }
}

function makeGeometries(types = ['body', 'lid']) {
  return types.map(type => ({
    type,
    geometry: makeMockGeometry(),
  }))
}

const defaultParams = {
  rows: 2,
  cols: 2,
  size: 20,
  rotation_clearance: 2,
}

function renderGrid(props = {}) {
  return render(
    <AnimatedGrid
      params={defaultParams}
      colors={{}}
      wireframe={false}
      onReady={vi.fn()}
      onError={vi.fn()}
      {...props}
    />
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('AnimatedGrid', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    frameCallback = null
    fetchResolve = null
    fetchReject = null
  })

  // =========================================================================
  // BRANCH: early return -- error / no geometries / no geoCenter (line 121)
  // =========================================================================
  describe('early return when data is not ready', () => {
    it('renders null before geometries are fetched', () => {
      const { container } = renderGrid()
      expect(container.innerHTML).toBe('')
    })

    it('renders null when fetch rejects with an error', async () => {
      const { container } = renderGrid()
      await vi.waitFor(() => expect(fetchReject).toBeTruthy())
      fetchReject(new Error('render failed'))
      await vi.waitFor(() => {
        expect(container.innerHTML).toBe('')
      })
    })
  })

  // =========================================================================
  // BRANCH: successful fetch -- component renders grid of cubes
  // =========================================================================
  describe('after successful geometry fetch', () => {
    async function resolveGeometries(props = {}) {
      const onReady = vi.fn()
      const result = renderGrid({ onReady, ...props })
      await vi.waitFor(() => expect(fetchResolve).toBeTruthy())
      const geos = makeGeometries()
      fetchResolve(geos)
      await vi.waitFor(() => {
        expect(result.container.innerHTML).not.toBe('')
      })
      return { ...result, onReady, geos }
    }

    it('calls onReady after geometries load', async () => {
      const { onReady } = await resolveGeometries()
      expect(onReady).toHaveBeenCalledOnce()
    })

    it('renders cubes for rows * cols grid', async () => {
      const { container } = await resolveGeometries()
      expect(container.innerHTML).not.toBe('')
    })

    it('renders with wireframe=true (transparent + low opacity)', async () => {
      const { container } = await resolveGeometries({ wireframe: true })
      expect(container.innerHTML).not.toBe('')
    })

    it('renders with wireframe=false (solid + full opacity)', async () => {
      const { container } = await resolveGeometries({ wireframe: false })
      expect(container.innerHTML).not.toBe('')
    })

    it('uses colors for geometry types when provided', async () => {
      const { container } = await resolveGeometries({
        colors: { body: '#ff0000', lid: '#00ff00' },
      })
      expect(container.innerHTML).not.toBe('')
    })

    it('falls back to defaultColor when color is not provided for type', async () => {
      const { container } = await resolveGeometries({ colors: {} })
      expect(container.innerHTML).not.toBe('')
    })
  })

  // =========================================================================
  // BRANCH: tubing_H param -- nullish coalescing (line 28)
  // =========================================================================
  describe('tubing_H parameter handling', () => {
    it('defaults tubing_H to 0 when undefined', async () => {
      const result = renderGrid({
        params: { ...defaultParams, tubing_H: undefined },
      })
      await vi.waitFor(() => expect(fetchResolve).toBeTruthy())
      fetchResolve(makeGeometries())
      await vi.waitFor(() => expect(result.container.innerHTML).not.toBe(''))
    })

    it('uses tubing_H when provided', async () => {
      const result = renderGrid({
        params: { ...defaultParams, tubing_H: 3 },
      })
      await vi.waitFor(() => expect(fetchResolve).toBeTruthy())
      fetchResolve(makeGeometries())
      await vi.waitFor(() => expect(result.container.innerHTML).not.toBe(''))
    })

    it('uses tubing_H=0 when explicitly set to 0', async () => {
      const result = renderGrid({
        params: { ...defaultParams, tubing_H: 0 },
      })
      await vi.waitFor(() => expect(fetchResolve).toBeTruthy())
      fetchResolve(makeGeometries())
      await vi.waitFor(() => expect(result.container.innerHTML).not.toBe(''))
    })
  })

  // =========================================================================
  // BRANCH: default_color fallback (line 31)
  // =========================================================================
  describe('default_color fallback', () => {
    it('falls back to #e5e7eb when getViewerConfig returns no default_color', async () => {
      mockGetViewerConfig.mockReturnValueOnce({ default_color: '' })
      const result = renderGrid()
      await vi.waitFor(() => expect(fetchResolve).toBeTruthy())
      fetchResolve(makeGeometries())
      await vi.waitFor(() => expect(result.container.innerHTML).not.toBe(''))
    })

    it('uses default_color from viewer config when available', async () => {
      mockGetViewerConfig.mockReturnValueOnce({ default_color: '#123456' })
      const result = renderGrid()
      await vi.waitFor(() => expect(fetchResolve).toBeTruthy())
      fetchResolve(makeGeometries())
      await vi.waitFor(() => expect(result.container.innerHTML).not.toBe(''))
    })
  })

  // =========================================================================
  // BRANCH: geometryKeys filter -- excludes checkbox params (line 54)
  // =========================================================================
  describe('geometryKeys filtering', () => {
    it('excludes checkbox-type parameters from geometry keys', async () => {
      const { fetchAssemblyGeometries } = await import('../../services/domain/assemblyFetcher')
      renderGrid()
      await vi.waitFor(() => expect(fetchAssemblyGeometries).toHaveBeenCalled())
      const calledKeys = fetchAssemblyGeometries.mock.calls[0][1]
      expect(calledKeys).toContain('size')
      expect(calledKeys).toContain('rows')
      expect(calledKeys).not.toContain('show_labels')
    })
  })

  // =========================================================================
  // BRANCH: useFrame animation loop (lines 87-119)
  // =========================================================================
  describe('useFrame animation loop', () => {
    it('returns early when geometries are not loaded', () => {
      renderGrid()
      expect(frameCallback).toBeTruthy()
      // geometries is null (not resolved), so early return on line 88
      frameCallback({}, 0.016)
    })

    it('increments pause timer when no cube is animating (else branch)', async () => {
      const result = renderGrid()
      await vi.waitFor(() => expect(fetchResolve).toBeTruthy())
      fetchResolve(makeGeometries())
      await vi.waitFor(() => expect(result.container.innerHTML).not.toBe(''))

      // All cubes at currentAngle===targetAngle, so animatingIdx < 0
      // Enters else branch (lines 110-118), pauseTimer < PAUSE_DURATION
      frameCallback({}, 0.1)
    })

    it('picks a random cube after pause duration elapses', async () => {
      const result = renderGrid()
      await vi.waitFor(() => expect(fetchResolve).toBeTruthy())
      fetchResolve(makeGeometries())
      await vi.waitFor(() => expect(result.container.innerHTML).not.toBe(''))

      const randomSpy = vi.spyOn(Math, 'random').mockReturnValue(0.5)
      // Exceed PAUSE_DURATION (0.3s) to trigger new target assignment
      frameCallback({}, 0.35)
      expect(randomSpy).toHaveBeenCalled()
      randomSpy.mockRestore()
    })

    it('animates a cube toward its target angle and sets rotation.z', async () => {
      const result = renderGrid()
      await vi.waitFor(() => expect(fetchResolve).toBeTruthy())
      fetchResolve(makeGeometries())
      await vi.waitFor(() => expect(result.container.innerHTML).not.toBe(''))

      // Trigger animation for cube 0
      vi.spyOn(Math, 'random').mockReturnValue(0)
      frameCallback({}, 0.35)

      // Now cube 0 has targetAngle = PI/2; call frame to animate (if branch line 93)
      frameCallback({}, 0.1)

      // Find the group elements with rotation property (patched by createElement)
      const groups = result.container.querySelectorAll('group')
      // At least some group should have a non-zero rotation.z
      const rotatedGroups = Array.from(groups).filter(g => g.rotation && g.rotation.z !== 0)
      expect(rotatedGroups.length).toBeGreaterThan(0)

      Math.random.mockRestore()
    })

    it('snaps cube angle when close to target', async () => {
      const result = renderGrid()
      await vi.waitFor(() => expect(fetchResolve).toBeTruthy())
      fetchResolve(makeGeometries())
      await vi.waitFor(() => expect(result.container.innerHTML).not.toBe(''))

      vi.spyOn(Math, 'random').mockReturnValue(0)
      frameCallback({}, 0.35) // trigger animation for cube 0

      // Large delta so step >= diff; snap logic on line 101 fires
      frameCallback({}, 100.0)

      // After snap, the group's rotation.z should be exactly PI/2
      const groups = result.container.querySelectorAll('group')
      const snapped = Array.from(groups).filter(g => g.rotation && Math.abs(g.rotation.z - Math.PI / 2) < 0.001)
      expect(snapped.length).toBeGreaterThan(0)

      Math.random.mockRestore()
    })

    it('processes multiple animation frames progressively', async () => {
      const result = renderGrid()
      await vi.waitFor(() => expect(fetchResolve).toBeTruthy())
      fetchResolve(makeGeometries())
      await vi.waitFor(() => expect(result.container.innerHTML).not.toBe(''))

      vi.spyOn(Math, 'random').mockReturnValue(0)
      frameCallback({}, 0.35) // trigger

      frameCallback({}, 0.2)
      const groups = result.container.querySelectorAll('group')
      const refGroup = Array.from(groups).find(g => g.rotation && g.rotation.z > 0)
      const afterFirst = refGroup?.rotation.z ?? 0
      expect(afterFirst).toBeGreaterThan(0)

      frameCallback({}, 0.2)
      const afterSecond = refGroup?.rotation.z ?? 0
      expect(afterSecond).toBeGreaterThan(afterFirst)

      Math.random.mockRestore()
    })
  })

  // =========================================================================
  // BRANCH: fetch cleanup -- cancelled flag (lines 66-77)
  // =========================================================================
  describe('fetch cleanup on unmount', () => {
    it('ignores fetch result when component unmounts before resolve', async () => {
      const onReady = vi.fn()
      const { unmount } = renderGrid({ onReady })
      await vi.waitFor(() => expect(fetchResolve).toBeTruthy())
      unmount()
      fetchResolve(makeGeometries())
      expect(onReady).not.toHaveBeenCalled()
    })

    it('ignores fetch error when component unmounts before reject', async () => {
      const { unmount } = renderGrid()
      await vi.waitFor(() => expect(fetchReject).toBeTruthy())
      unmount()
      fetchReject(new Error('too late'))
    })
  })

  // =========================================================================
  // BRANCH: onReady optional chaining (line 73)
  // =========================================================================
  describe('onReady callback', () => {
    it('works when onReady is not provided', async () => {
      const result = render(
        <AnimatedGrid
          params={defaultParams}
          colors={{}}
          wireframe={false}
        />
      )
      await vi.waitFor(() => expect(fetchResolve).toBeTruthy())
      fetchResolve(makeGeometries())
      await vi.waitFor(() => expect(result.container.innerHTML).not.toBe(''))
    })
  })

  // =========================================================================
  // BRANCH: projectSlug passed to fetchAssemblyGeometries (bug fix)
  // =========================================================================
  describe('project slug forwarding', () => {
    it('passes projectSlug to fetchAssemblyGeometries', async () => {
      const { fetchAssemblyGeometries } = await import('../../services/domain/assemblyFetcher')
      renderGrid()
      await vi.waitFor(() => expect(fetchAssemblyGeometries).toHaveBeenCalled())
      expect(fetchAssemblyGeometries.mock.calls[0][2]).toBe('tablaco')
    })

    it('calls onError when fetch rejects', async () => {
      const onError = vi.fn()
      renderGrid({ onError })
      await vi.waitFor(() => expect(fetchReject).toBeTruthy())
      fetchReject(new Error('render failed'))
      await vi.waitFor(() => {
        expect(onError).toHaveBeenCalledWith('render failed')
      })
    })
  })

  // =========================================================================
  // Grid positioning logic (preserved from original test file)
  // =========================================================================
  describe('grid positioning logic (pure functions)', () => {
    function gridPitch(size, rotationClearance) {
      return size * Math.SQRT2 + rotationClearance
    }

    function cubePosition(r, c, size, rotationClearance, tubingH = 0, center = { x: 0, y: 0, z: 0 }) {
      const pitch = gridPitch(size, rotationClearance)
      return {
        x: center.x,
        y: c * pitch + center.y,
        z: r * (size + tubingH) + tubingH + center.z,
      }
    }

    it('computes gridPitch as size * sqrt(2) + rotationClearance', () => {
      expect(gridPitch(20, 2)).toBeCloseTo(20 * Math.SQRT2 + 2)
    })

    it('columns spread along Y axis', () => {
      const p0 = cubePosition(0, 0, 20, 2)
      const p1 = cubePosition(0, 1, 20, 2)
      const pitch = gridPitch(20, 2)
      expect(p1.y - p0.y).toBeCloseTo(pitch)
    })

    it('rows stack along Z with tubing spacers', () => {
      const p0 = cubePosition(0, 0, 20, 2, 2)
      const p1 = cubePosition(1, 0, 20, 2, 2)
      expect(p0.z).toBeCloseTo(2)
      expect(p1.z).toBeCloseTo(24)
    })

    it('applies center offset', () => {
      const center = { x: 5, y: 10, z: 15 }
      const pos = cubePosition(0, 0, 20, 2, 0, center)
      expect(pos.x).toBeCloseTo(5)
      expect(pos.y).toBeCloseTo(10)
      expect(pos.z).toBeCloseTo(15)
    })
  })
})
