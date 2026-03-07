import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

// Mock Three.js and R3F to avoid jsdom issues
vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: any) => <div data-testid="canvas">{children}</div>,
  useFrame: () => {},
  useLoader: () => null,
}))
vi.mock('@react-three/drei', () => ({
  ScrollControls: ({ children }: any) => <div>{children}</div>,
  Scroll: ({ children }: any) => <div>{children}</div>,
  useScroll: () => ({ offset: 0 }),
  Environment: () => null,
  ContactShadows: () => null,
  Image: () => null,
  useGLTF: () => null,
}))
vi.mock('three', () => ({
  Vector3: class { x = 0; y = 0; z = 0; lerp() { return this } },
  Box3: class { setFromObject() { return this }; getCenter(v: any) { return v }; getSize(v: any) { return v } },
  Group: class {},
  MeshStandardMaterial: class {},
}))
vi.mock('three/examples/jsm/loaders/GLTFLoader.js', () => ({
  GLTFLoader: class {},
}))
vi.mock('./GLBErrorBoundary', () => ({
  GLBErrorBoundary: ({ children }: any) => <>{children}</>,
}))

import ProjectCarousel3D from './ProjectCarousel3D'

const MANIFEST_RESPONSE = {
  generated: '2026-03-07T00:00:00Z',
  models: [
    { slug: 'gridfinity', size: 14380 },
    { slug: 'framing-hyperobject', size: 17360 },
  ],
}

const MOCK_PROJECTS = [
  { slug: 'gridfinity', name: 'Gridfinity', description: 'Storage bins', descriptionEs: 'Contenedores', category: 'storage', isHyperobject: true },
  { slug: 'framing-hyperobject', name: 'Framing', description: 'Framing', descriptionEs: 'Enmarcado', category: 'art', isHyperobject: true },
  { slug: 'gear-reducer', name: 'Gear Reducer', description: 'Gears', descriptionEs: 'Engranes', category: 'mechanical', isHyperobject: true },
]

describe('ProjectCarousel3D', () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, 'fetch')
  })

  afterEach(() => {
    fetchSpy.mockRestore()
  })

  it('fetches manifest.json on mount', async () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MANIFEST_RESPONSE),
    } as Response)

    render(
      <ProjectCarousel3D
        projects={MOCK_PROJECTS}
        searchQuery=""
        setSearchQuery={() => {}}
        activeCategory="all"
        setActiveCategory={() => {}}
        activeDomain="all"
        setActiveDomain={() => {}}
      />
    )

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('/models/manifest.json')
    })
  })

  it('handles manifest fetch failure gracefully', async () => {
    fetchSpy.mockRejectedValue(new Error('Network error'))

    render(
      <ProjectCarousel3D
        projects={MOCK_PROJECTS}
        searchQuery=""
        setSearchQuery={() => {}}
        activeCategory="all"
        setActiveCategory={() => {}}
        activeDomain="all"
        setActiveDomain={() => {}}
      />
    )

    // Should render without crashing even when manifest fetch fails
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('/models/manifest.json')
    })
    expect(screen.getByTestId('canvas')).toBeInTheDocument()
  })

  it('handles non-OK manifest response gracefully', async () => {
    fetchSpy.mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.reject(new Error('Not found')),
    } as any)

    render(
      <ProjectCarousel3D
        projects={MOCK_PROJECTS}
        searchQuery=""
        setSearchQuery={() => {}}
        activeCategory="all"
        setActiveCategory={() => {}}
        activeDomain="all"
        setActiveDomain={() => {}}
      />
    )

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('/models/manifest.json')
    })
    expect(screen.getByTestId('canvas')).toBeInTheDocument()
  })

  it('renders empty state when no projects', () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ models: [] }),
    } as Response)

    render(
      <ProjectCarousel3D
        projects={[]}
        searchQuery=""
        setSearchQuery={() => {}}
        activeCategory="all"
        setActiveCategory={() => {}}
        activeDomain="all"
        setActiveDomain={() => {}}
      />
    )

    expect(screen.getByText(/no se encontraron hyperobjetos/i)).toBeInTheDocument()
  })

  it('renders search input and category filters', () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MANIFEST_RESPONSE),
    } as Response)

    render(
      <ProjectCarousel3D
        projects={MOCK_PROJECTS}
        searchQuery=""
        setSearchQuery={() => {}}
        activeCategory="all"
        setActiveCategory={() => {}}
        activeDomain="all"
        setActiveDomain={() => {}}
      />
    )

    expect(screen.getByPlaceholderText(/buscar hyperobjetos/i)).toBeInTheDocument()
  })

  it('renders swipe/drag indicator when multiple projects', () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MANIFEST_RESPONSE),
    } as Response)

    render(
      <ProjectCarousel3D
        projects={MOCK_PROJECTS}
        searchQuery=""
        setSearchQuery={() => {}}
        activeCategory="all"
        setActiveCategory={() => {}}
        activeDomain="all"
        setActiveDomain={() => {}}
      />
    )

    expect(screen.getByText(/desliza para explorar/i)).toBeInTheDocument()
  })
})
