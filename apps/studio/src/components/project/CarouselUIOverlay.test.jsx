import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

// Mock lucide-react icons
import { vi } from 'vitest'
vi.mock('lucide-react', () => ({
    Settings2: () => <span data-testid="icon-settings" />,
    ArrowRight: () => <span data-testid="icon-arrow" />,
}))

// Mock shadcn Card components
vi.mock('@/components/ui/card', () => ({
    Card: ({ children, ...props }) => <div {...props}>{children}</div>,
    CardHeader: ({ children, ...props }) => <div {...props}>{children}</div>,
    CardTitle: ({ children, ...props }) => <h3 {...props}>{children}</h3>,
    CardDescription: ({ children, ...props }) => <p {...props}>{children}</p>,
    CardContent: ({ children, ...props }) => <div {...props}>{children}</div>,
    CardFooter: ({ children, ...props }) => <div {...props}>{children}</div>,
}))

vi.mock('@/components/ui/button', () => ({
    Button: ({ children, ...props }) => <button {...props}>{children}</button>,
}))

import CarouselUIOverlay from './CarouselUIOverlay'

const MOCK_PROJECT = {
    name: 'Test Model',
    slug: 'test-model',
    version: '2.0.0',
    description: { en: 'A parametric test model' },
    parameter_count: 12,
    difficulty: 'intermediate',
    is_hyperobject: true,
    tags: ['3d', 'parametric', 'lab'],
}

const renderWithRouter = (ui) =>
    render(<MemoryRouter>{ui}</MemoryRouter>)

describe('CarouselUIOverlay', () => {
    const defaultProps = {
        project: MOCK_PROJECT,
        loc: (val) => (typeof val === 'object' ? val.en : val),
        index: 2,
        total: 5,
    }

    it('renders null when no project', () => {
        const { container } = renderWithRouter(
            <CarouselUIOverlay project={null} loc={(v) => v} index={0} total={0} />
        )
        expect(container.innerHTML).toBe('')
    })

    it('renders project name', () => {
        renderWithRouter(<CarouselUIOverlay {...defaultProps} />)
        expect(screen.getByText('Test Model')).toBeInTheDocument()
    })

    it('renders version badge', () => {
        renderWithRouter(<CarouselUIOverlay {...defaultProps} />)
        expect(screen.getByText('v2.0.0')).toBeInTheDocument()
    })

    it('renders description', () => {
        renderWithRouter(<CarouselUIOverlay {...defaultProps} />)
        expect(screen.getByText('A parametric test model')).toBeInTheDocument()
    })

    it('shows parameter count', () => {
        renderWithRouter(<CarouselUIOverlay {...defaultProps} />)
        expect(screen.getByText('12 Params')).toBeInTheDocument()
    })

    it('shows difficulty', () => {
        renderWithRouter(<CarouselUIOverlay {...defaultProps} />)
        expect(screen.getByText('intermediate')).toBeInTheDocument()
    })

    it('shows Hyperobject badge', () => {
        renderWithRouter(<CarouselUIOverlay {...defaultProps} />)
        expect(screen.getByText('Hyperobject')).toBeInTheDocument()
    })

    it('shows tag badges', () => {
        renderWithRouter(<CarouselUIOverlay {...defaultProps} />)
        expect(screen.getByText('3d')).toBeInTheDocument()
        expect(screen.getByText('parametric')).toBeInTheDocument()
        expect(screen.getByText('lab')).toBeInTheDocument()
    })

    it('shows pagination (index/total)', () => {
        renderWithRouter(<CarouselUIOverlay {...defaultProps} />)
        // Pagination rendered as "3 / 5" with nested spans — match the combined text
        expect(screen.getByText((_, el) =>
            el?.className?.includes('font-medium') && el?.textContent?.includes('3') && el?.textContent?.includes('5')
        )).toBeInTheDocument()
    })

    it('links to project studio', () => {
        renderWithRouter(<CarouselUIOverlay {...defaultProps} />)
        const link = screen.getByText('Open Studio').closest('a')
        expect(link).toHaveAttribute('href', '/project/test-model')
    })

    it('renders outside any Router (drei <Scroll html> mounts it in its own React root)', () => {
        // Production 2026-10-18: a react-router <Link> here threw "Cannot destructure
        // property 'basename' of useContext(...)" and took the 3D catalog down.
        render(<CarouselUIOverlay {...defaultProps} />)
        expect(screen.getByText('Open Studio').closest('a')).toHaveAttribute('href', '/project/test-model')
    })

    it('opens the project client-side through onOpen', () => {
        const onOpen = vi.fn()
        render(<CarouselUIOverlay {...defaultProps} onOpen={onOpen} />)
        const link = screen.getByText('Open Studio').closest('a')
        const plain = new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 })
        link.dispatchEvent(plain)
        expect(onOpen).toHaveBeenCalledWith('test-model')
        expect(plain.defaultPrevented).toBe(true)
    })

    it('leaves modifier clicks to the browser (open in a new tab)', () => {
        const onOpen = vi.fn()
        render(<CarouselUIOverlay {...defaultProps} onOpen={onOpen} />)
        const link = screen.getByText('Open Studio').closest('a')
        const newTab = new MouseEvent('click', { bubbles: true, cancelable: true, button: 0, metaKey: true })
        link.dispatchEvent(newTab)
        expect(onOpen).not.toHaveBeenCalled()
        expect(newTab.defaultPrevented).toBe(false)
    })
})
