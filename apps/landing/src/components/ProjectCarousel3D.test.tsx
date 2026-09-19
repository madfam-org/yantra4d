import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock Three.js and R3F to avoid jsdom issues
vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children, frameloop }: any) => <div data-testid="canvas" data-frameloop={frameloop}>{children}</div>,
  useFrame: () => {},
  useLoader: () => null,
}))
vi.mock('@react-three/drei', () => ({
  ScrollControls: ({ children }: any) => <div>{children}</div>,
  Scroll: ({ children }: any) => <div>{children}</div>,
  useScroll: () => ({ offset: 0 }),
  Environment: () => null,
  ContactShadows: () => null,
}))
vi.mock('three', () => ({
  Vector3: class { x = 0; y = 0; z = 0; set() { return this } lerp() { return this } },
  Box3: class { setFromObject() { return this }; getCenter(v: any) { return v }; getSize(v: any) { return v } },
  Group: class {},
  MeshStandardMaterial: class {},
}))
vi.mock('three/examples/jsm/loaders/GLTFLoader.js', () => ({ GLTFLoader: class { setMeshoptDecoder() {} } }))
vi.mock('three/examples/jsm/libs/meshopt_decoder.module.js', () => ({ MeshoptDecoder: {} }))
vi.mock('./GLBErrorBoundary', () => ({ GLBErrorBoundary: ({ children }: any) => <>{children}</> }))

import ProjectCarousel3D from './ProjectCarousel3D'
import type { GalleryLabels } from './CommonsGallery'

const LABELS: GalleryLabels = {
  search: 'Buscar', allCategories: 'Todas', allDomains: 'Todos', showMore: 'Ver más', showing: '{shown}/{total}',
  inThreeD: 'Mostrando {shown} de {total} en 3D', noResults: 'No se encontraron hiperobjetos.', openStudio: 'Abrir Studio',
  openInStudio: 'Abrir en Studio →', swipe: 'Desliza para explorar', drag: 'Arrastra para explorar', prev: 'Proyecto anterior',
  next: 'Proyecto siguiente', live: 'Render 3D en vivo', stillStrip: 'Selección', hyperobject: 'Hiperobjeto', loading: 'Cargando…',
  categories: { storage: 'Almacenamiento', art: 'Arte', mechanical: 'Mecánico' }, domains: {},
}

const MANIFEST = {
  version: 2,
  generated: '2026-09-19T00:00:00Z',
  models: [
    { slug: 'gridfinity', size: 9000, lod1: { file: 'gridfinity.lod1.glb', bytes: 9000, triangles: 2000 } },
    { slug: 'framing-hyperobject', size: 17360 },
  ],
}

const PROJECTS = [
  { slug: 'gridfinity', name: 'Gridfinity', description: 'Contenedores', category: 'storage', thumbnail: '/p/g.webp', isHyperobject: true, domain: 'household' },
  { slug: 'framing-hyperobject', name: 'Framing', description: 'Enmarcado', category: 'art', thumbnail: '/p/f.webp', isHyperobject: true, domain: 'household' },
  { slug: 'gear-reducer', name: 'Gear Reducer', description: 'Engranes', category: 'mechanical', thumbnail: '/p/r.webp', isHyperobject: true, domain: 'industrial' },
]

const renderStage = (over: Partial<React.ComponentProps<typeof ProjectCarousel3D>> = {}) =>
  render(
    <ProjectCarousel3D
      tier="full"
      labels={LABELS}
      projects={PROJECTS}
      manifest={MANIFEST as any}
      studioUrl="https://app.example.test"
      {...over}
    />,
  )

describe('ProjectCarousel3D', () => {
  it('mounts the stage root the page contract names, with the canvas inside', () => {
    renderStage()
    const stage = screen.getByTestId('commons-stage')
    expect(stage).toHaveAttribute('data-stage-tier', 'full')
    expect(screen.getByTestId('canvas')).toBeInTheDocument()
  })

  it('renders while visible (jsdom IntersectionObserver stub never fires)', () => {
    renderStage()
    expect(screen.getByTestId('canvas')).toHaveAttribute('data-frameloop', 'always')
  })

  it('shows the active project card with a Studio link', () => {
    renderStage()
    expect(screen.getByRole('heading', { name: 'Gridfinity' })).toBeInTheDocument()
    const link = screen.getByRole('link', { name: /Abrir Studio/ })
    expect(link).toHaveAttribute('href', 'https://app.example.test/project/gridfinity')
    expect(screen.getByTestId('stage-counter')).toHaveTextContent('1 / 3')
  })

  it('steps through projects with the previous / next controls', () => {
    renderStage()
    fireEvent.click(screen.getByRole('button', { name: 'Proyecto siguiente' }))
    expect(screen.getByRole('heading', { name: 'Framing' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Proyecto anterior' }))
    fireEvent.click(screen.getByRole('button', { name: 'Proyecto anterior' }))
    expect(screen.getByRole('heading', { name: 'Gear Reducer' })).toBeInTheDocument()
  })

  it('renders the empty state from the labels when no projects', () => {
    renderStage({ projects: [] })
    expect(screen.getByText('No se encontraron hiperobjetos.')).toBeInTheDocument()
  })

  it('renders the note and the swipe/drag hint', () => {
    renderStage({ note: 'Mostrando 3 de 40 en 3D' })
    expect(screen.getByText('Mostrando 3 de 40 en 3D')).toBeInTheDocument()
    expect(screen.getByText(/para explorar/)).toBeInTheDocument()
  })

  it('carries the tier onto the stage for the lite variant', () => {
    renderStage({ tier: 'lite' })
    expect(screen.getByTestId('commons-stage')).toHaveAttribute('data-stage-tier', 'lite')
  })
})
