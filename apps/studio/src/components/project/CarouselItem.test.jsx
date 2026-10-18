import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'

// Mock R3F
vi.mock('@react-three/fiber', () => ({
    useFrame: vi.fn(),
    Canvas: ({ children }) => <div data-testid="mock-canvas">{children}</div>,
}))

// Mock Drei
vi.mock('@react-three/drei', () => ({
    Image: (props) => {
        // drei's <Image> throws when its texture cannot be loaded
        if (props.url.includes('missing')) throw new Error(`Could not load ${props.url}: undefined`)
        return <div data-testid="drei-image" data-url={props.url} />
    },
    useGLTF: () => ({ scene: null }),
}))

// Mock THREE
vi.mock('three', () => ({
    Vector3: function (x, y, z) {
        this.x = x || 0
        this.y = y || 0
        this.z = z || 0
        return this
    },
    Box3: function () {
        this.setFromObject = vi.fn(() => this)
        this.getCenter = vi.fn(() => ({ x: 0, y: 0, z: 0 }))
        this.getSize = vi.fn(() => ({ x: 1, y: 1, z: 1 }))
        return this
    },
}))

// Mock renderService
vi.mock('../../services/engine/renderService', () => ({
    renderParts: vi.fn(() => Promise.resolve([])),
}))

import CarouselItem, { liveRenderMode } from './CarouselItem'

const MOCK_PROJECT = {
    slug: 'test-model',
    name: 'Test Model',
    thumbnail: '/thumbs/test.png',
    parameters: [
        { id: 'height', default: 10 },
        { id: 'width', default: 20 },
    ],
    modes: [{ id: 'default' }],
}

describe('CarouselItem', () => {
    it('renders without crash', () => {
        // R3F components render as simple DOM in tests
        const { container } = render(
            <CarouselItem
                project={MOCK_PROJECT}
                position={[0, 0, 0]}
                gap={4}
            />
        )
        expect(container).toBeTruthy()
    })

    it('renders with project data', () => {
        const { container } = render(
            <CarouselItem
                project={MOCK_PROJECT}
                position={[4, 0, 0]}
                gap={4}
            />
        )
        // Component renders as group elements in R3F mock
        expect(container).toBeTruthy()
    })

    it('handles project without thumbnail', () => {
        const projectNoThumb = { ...MOCK_PROJECT, thumbnail: null }
        const { container } = render(
            <CarouselItem
                project={projectNoThumb}
                position={[0, 0, 0]}
                gap={4}
            />
        )
        expect(container).toBeTruthy()
    })

    it('handles project without parameters', () => {
        const projectNoParams = { ...MOCK_PROJECT, parameters: undefined }
        const { container } = render(
            <CarouselItem
                project={projectNoParams}
                position={[0, 0, 0]}
                gap={4}
            />
        )
        expect(container).toBeTruthy()
    })

    it('drops a thumbnail that cannot load instead of crashing the carousel', () => {
        // Production 2026-10-18: /projects/ab-drive.webp is not shipped, and the
        // whole 3D catalog showed "Could not load /projects/ab-drive.webp".
        const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
        const error = vi.spyOn(console, 'error').mockImplementation(() => {})
        const broken = { ...MOCK_PROJECT, slug: 'ab-drive', thumbnail: '/projects/missing.webp' }
        const { queryByTestId } = render(
            <>
                <CarouselItem project={broken} position={[4, 0, 0]} gap={4} />
                <CarouselItem project={{ ...MOCK_PROJECT, slug: 'ok' }} position={[8, 0, 0]} gap={4} />
            </>
        )
        // The broken item renders nothing; its neighbour still renders its thumbnail.
        expect(queryByTestId('drei-image')).toHaveAttribute('data-url', '/thumbs/test.png')
        expect(warn).toHaveBeenCalledWith(expect.stringContaining('ab-drive'), expect.stringContaining('missing.webp'))
        warn.mockRestore()
        error.mockRestore()
    })

    it('live-renders only with a real mode id (catalog records carry none)', () => {
        // Production 2026-10-18: every active item POSTed mode "default" and got
        // HTTP 400 invalid_mode_id_default, a red box and a spent render token.
        expect(liveRenderMode({ slug: 'a', mode_count: 3 })).toBeNull()
        expect(liveRenderMode({ slug: 'a', modes: [] })).toBeNull()
        expect(liveRenderMode({ slug: 'a', modes: [{ id: '' }] })).toBeNull()
        expect(liveRenderMode({ slug: 'a', modes: [{ id: 'cup' }, { id: 'lid' }] })).toBe('cup')
    })
})
