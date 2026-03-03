import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
    AlertTriangle: () => <span data-testid="icon-alert" />,
    ChevronLeft: () => <span data-testid="icon-left" />,
    ChevronRight: () => <span data-testid="icon-right" />,
}))

// Mock shadcn Button
vi.mock('@/components/ui/button', () => ({
    Button: ({ children, ...props }) => <button {...props}>{children}</button>,
}))

import ReviewStep from './ReviewStep'

const mockT = (key) => {
    const map = {
        'onboard.review_title': 'Review Analysis',
        'onboard.warnings': 'Warnings',
        'onboard.variables': 'Variables',
        'onboard.modules': 'Modules',
        'onboard.includes': 'Includes',
        'onboard.render_modes': 'Render Modes',
        'onboard.none': 'None',
        'onboard.back': 'Back',
        'onboard.edit_manifest': 'Edit Manifest',
    }
    return map[key] || key
}

const defaultProps = {
    analysis: {
        files: {
            'main.scad': {
                variables: ['height', 'width'],
                modules: ['base_plate'],
                includes: ['BOSL2/std.scad'],
                render_modes: ['default', 'grid'],
            },
        },
    },
    warnings: [],
    onBack: vi.fn(),
    onNext: vi.fn(),
    t: mockT,
}

describe('ReviewStep', () => {
    it('renders without crash', () => {
        render(<ReviewStep {...defaultProps} />)
        expect(screen.getByText('Review Analysis')).toBeInTheDocument()
    })

    it('hides warnings section when no warnings', () => {
        render(<ReviewStep {...defaultProps} />)
        expect(screen.queryByText('Warnings')).not.toBeInTheDocument()
    })

    it('shows warnings when present', () => {
        render(<ReviewStep {...defaultProps} warnings={['Missing include', 'No render_mode found']} />)
        expect(screen.getByText('Warnings')).toBeInTheDocument()
        expect(screen.getByText('Missing include')).toBeInTheDocument()
        expect(screen.getByText('No render_mode found')).toBeInTheDocument()
    })

    it('renders file analysis data', () => {
        render(<ReviewStep {...defaultProps} />)
        expect(screen.getByText('main.scad')).toBeInTheDocument()
        expect(screen.getByText('Variables: 2')).toBeInTheDocument()
        expect(screen.getByText('Modules: 1')).toBeInTheDocument()
        expect(screen.getByText('Includes: 1')).toBeInTheDocument()
        expect(screen.getByText('Render Modes: default, grid')).toBeInTheDocument()
    })

    it('shows "None" for empty render modes', () => {
        const analysis = {
            files: {
                'test.scad': {
                    variables: [],
                    modules: [],
                    includes: [],
                    render_modes: [],
                },
            },
        }
        render(<ReviewStep {...defaultProps} analysis={analysis} />)
        expect(screen.getByText('Render Modes: None')).toBeInTheDocument()
    })

    it('calls onBack when back button clicked', () => {
        const onBack = vi.fn()
        render(<ReviewStep {...defaultProps} onBack={onBack} />)
        fireEvent.click(screen.getByText('Back'))
        expect(onBack).toHaveBeenCalledOnce()
    })

    it('calls onNext when next button clicked', () => {
        const onNext = vi.fn()
        render(<ReviewStep {...defaultProps} onNext={onNext} />)
        fireEvent.click(screen.getByText('Edit Manifest'))
        expect(onNext).toHaveBeenCalledOnce()
    })
})
