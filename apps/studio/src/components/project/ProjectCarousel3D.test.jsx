import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

// Mock LanguageProvider
vi.mock('../../contexts/system/LanguageProvider', () => ({
    useLanguage: () => ({
        t: (key, fallback) => fallback || key,
        language: 'en',
    }),
}))

// Mock R3F
vi.mock('@react-three/fiber', () => ({
    Canvas: ({ children }) => <div data-testid="r3f-canvas">{children}</div>,
    useFrame: vi.fn(),
}))

// Mock Drei
vi.mock('@react-three/drei', () => ({
    ScrollControls: ({ children }) => <div data-testid="scroll-controls">{children}</div>,
    Scroll: ({ children }) => <div data-testid="scroll">{children}</div>,
    useScroll: () => ({ offset: 0 }),
    Environment: () => null,
    ContactShadows: () => null,
}))

// Mock child components
vi.mock('./CarouselItem', () => ({
    default: ({ project }) => <div data-testid={`carousel-item-${project.slug}`} />,
}))

vi.mock('./CarouselUIOverlay', () => ({
    default: ({ project, onOpen }) => (
        <button type="button" data-testid="carousel-overlay" onClick={() => onOpen?.(project.slug)}>{project?.name}</button>
    ),
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', () => ({
    useNavigate: () => mockNavigate,
}))

import ProjectCarousel3D from './ProjectCarousel3D'

const MOCK_PROJECTS = [
    { slug: 'model-a', name: 'Model A', description: 'First' },
    { slug: 'model-b', name: 'Model B', description: 'Second' },
]

describe('ProjectCarousel3D', () => {
    it('renders null when no projects', () => {
        const { container } = render(<ProjectCarousel3D projects={[]} />)
        expect(container.innerHTML).toBe('')
    })

    it('renders canvas with projects', () => {
        render(<ProjectCarousel3D projects={MOCK_PROJECTS} />)
        expect(screen.getByTestId('r3f-canvas')).toBeInTheDocument()
    })

    it('renders carousel items for each project', () => {
        render(<ProjectCarousel3D projects={MOCK_PROJECTS} />)
        expect(screen.getByTestId('carousel-item-model-a')).toBeInTheDocument()
        expect(screen.getByTestId('carousel-item-model-b')).toBeInTheDocument()
    })

    it('renders the UI overlay with first project active by default', () => {
        render(<ProjectCarousel3D projects={MOCK_PROJECTS} />)
        expect(screen.getByTestId('carousel-overlay')).toBeInTheDocument()
        expect(screen.getByText('Model A')).toBeInTheDocument()
    })

    it('hands the overlay a client-side navigation to the project', () => {
        render(<ProjectCarousel3D projects={MOCK_PROJECTS} />)
        screen.getByTestId('carousel-overlay').click()
        expect(mockNavigate).toHaveBeenCalledWith('/project/model-a')
    })
})
