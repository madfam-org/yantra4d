import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const mockPatchFlags = vi.fn()

vi.mock('../../hooks/useAdminProjects', () => ({
    useAdminProjects: () => ({
        patchFlags: mockPatchFlags,
    }),
}))

vi.mock('@/components/ui/switch', () => ({
    Switch: ({ checked, onCheckedChange, 'aria-label': ariaLabel, ...props }) => (
        <button
            role="switch"
            aria-checked={checked}
            aria-label={ariaLabel}
            onClick={onCheckedChange}
            {...props}
        />
    ),
}))
vi.mock('lucide-react', () => ({
    Loader2: (props) => <span data-testid="loader" {...props} />,
    Check: (props) => <span {...props} />,
    X: (props) => <span {...props} />,
    EyeOff: (props) => <span {...props} />,
}))

import ProjectFlagsRow from './ProjectFlagsRow'

describe('ProjectFlagsRow', () => {
    const defaultProject = {
        slug: 'gridfinity',
        is_demo: false,
        is_hyperobject: true,
        unlisted: false,
        mode_count: 3,
        parameter_count: 10,
    }

    beforeEach(() => {
        mockPatchFlags.mockReset()
        mockPatchFlags.mockResolvedValue({ updated: {} })
    })

    const renderRow = (project = defaultProject) =>
        render(
            <table><tbody>
                <ProjectFlagsRow project={project} isLast={false} />
            </tbody></table>
        )

    it('renders project slug', () => {
        renderRow()
        expect(screen.getByText('gridfinity')).toBeInTheDocument()
    })

    it('renders demo toggle switch', () => {
        renderRow()
        expect(screen.getByRole('switch', { name: /toggle demo for gridfinity/i })).toBeInTheDocument()
    })

    it('renders hyperobject toggle switch', () => {
        renderRow()
        expect(screen.getByRole('switch', { name: /toggle hyperobject for gridfinity/i })).toBeInTheDocument()
    })

    it('calls patchFlags when demo switch toggled', async () => {
        renderRow()
        fireEvent.click(screen.getByRole('switch', { name: /toggle demo/i }))
        await waitFor(() => {
            expect(mockPatchFlags).toHaveBeenCalledWith('gridfinity', { is_demo: true })
        })
    })

    it('calls patchFlags when hyperobject switch toggled', async () => {
        renderRow()
        fireEvent.click(screen.getByRole('switch', { name: /toggle hyperobject/i }))
        await waitFor(() => {
            expect(mockPatchFlags).toHaveBeenCalledWith('gridfinity', { is_hyperobject: false })
        })
    })

    it('shows toast on successful toggle', async () => {
        renderRow()
        fireEvent.click(screen.getByRole('switch', { name: /toggle demo/i }))
        await waitFor(() => {
            expect(screen.getByText(/demo/)).toBeInTheDocument()
        })
    })

    it('shows error toast on failed toggle', async () => {
        mockPatchFlags.mockRejectedValueOnce(new Error('Forbidden'))
        renderRow()
        fireEvent.click(screen.getByRole('switch', { name: /toggle demo/i }))
        await waitFor(() => {
            expect(screen.getByText(/Forbidden/)).toBeInTheDocument()
        })
    })

    it('renders unlisted toggle switch', () => {
        renderRow()
        expect(screen.getByRole('switch', { name: /toggle unlisted for gridfinity/i })).toBeInTheDocument()
    })

    it('calls patchFlags when unlisted switch toggled', async () => {
        renderRow()
        fireEvent.click(screen.getByRole('switch', { name: /toggle unlisted/i }))
        await waitFor(() => {
            expect(mockPatchFlags).toHaveBeenCalledWith('gridfinity', { unlisted: true })
        })
    })

    it('displays mode and parameter counts', () => {
        renderRow()
        expect(screen.getByText('3')).toBeInTheDocument()
        expect(screen.getByText('10')).toBeInTheDocument()
    })
})
