import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
    Check: () => <span data-testid="icon-check" />,
    ChevronLeft: () => <span data-testid="icon-left" />,
}))

// Mock shadcn Button
vi.mock('@/components/ui/button', () => ({
    Button: ({ children, disabled, ...props }) => (
        <button disabled={disabled} {...props}>{children}</button>
    ),
}))

import SaveStep from './SaveStep'

const mockT = (key) => {
    const map = {
        'onboard.save_title': 'Save Project',
        'onboard.back': 'Back',
        'onboard.saving': 'Saving...',
        'onboard.create_btn': 'Create Project',
        'onboard.cancel': 'Cancel',
    }
    return map[key] || key
}

const defaultProps = {
    saveSummary: 'Project will be saved to /projects/test',
    onBack: vi.fn(),
    onSave: vi.fn(),
    loading: false,
    t: mockT,
}

describe('SaveStep', () => {
    it('renders without crash', () => {
        render(<SaveStep {...defaultProps} />)
        expect(screen.getByText('Save Project')).toBeInTheDocument()
    })

    it('displays save summary text', () => {
        render(<SaveStep {...defaultProps} />)
        expect(screen.getByText('Project will be saved to /projects/test')).toBeInTheDocument()
    })

    it('shows "Create Project" when not loading', () => {
        render(<SaveStep {...defaultProps} />)
        expect(screen.getByText('Create Project')).toBeInTheDocument()
    })

    it('shows "Saving..." and disables button when loading', () => {
        render(<SaveStep {...defaultProps} loading={true} />)
        expect(screen.getByText('Saving...')).toBeInTheDocument()
        const saveBtn = screen.getByText('Saving...').closest('button')
        expect(saveBtn).toBeDisabled()
    })

    it('hides cancel button when onCancel not provided', () => {
        render(<SaveStep {...defaultProps} />)
        expect(screen.queryByText('Cancel')).not.toBeInTheDocument()
    })

    it('shows cancel button when onCancel provided', () => {
        const onCancel = vi.fn()
        render(<SaveStep {...defaultProps} onCancel={onCancel} />)
        expect(screen.getByText('Cancel')).toBeInTheDocument()
    })

    it('calls onBack when back button clicked', () => {
        const onBack = vi.fn()
        render(<SaveStep {...defaultProps} onBack={onBack} />)
        fireEvent.click(screen.getByText('Back'))
        expect(onBack).toHaveBeenCalledOnce()
    })

    it('calls onSave when save button clicked', () => {
        const onSave = vi.fn()
        render(<SaveStep {...defaultProps} onSave={onSave} />)
        fireEvent.click(screen.getByText('Create Project'))
        expect(onSave).toHaveBeenCalledOnce()
    })

    it('calls onCancel when cancel button clicked', () => {
        const onCancel = vi.fn()
        render(<SaveStep {...defaultProps} onCancel={onCancel} />)
        fireEvent.click(screen.getByText('Cancel'))
        expect(onCancel).toHaveBeenCalledOnce()
    })
})
