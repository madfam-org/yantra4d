import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

const mockRefresh = vi.fn()
const mockPatchFlags = vi.fn()

vi.mock('../../hooks/useAdminProjects', () => ({
    useAdminProjects: vi.fn(() => ({
        projects: [
            { slug: 'gridfinity', name: 'Gridfinity Extended', is_demo: true, is_hyperobject: false, modes_count: 3, params_count: 10 },
            { slug: 'din-rail-clip', name: 'DIN Rail Clip', is_demo: false, is_hyperobject: true, modes_count: 1, params_count: 4 },
            { slug: 'voronoi', name: 'Voronoi', is_demo: false, is_hyperobject: false, modes_count: 2, params_count: 6 },
        ],
        loading: false,
        error: null,
        refresh: mockRefresh,
        patchFlags: mockPatchFlags,
    })),
}))

vi.mock('./ProjectFlagsRow', () => ({
    default: ({ project }) => (
        <tr data-testid={`flags-row-${project.slug}`}>
            <td>{project.slug}</td>
        </tr>
    ),
}))

vi.mock('@/components/ui/button', () => ({
    Button: ({ children, ...props }) => <button {...props}>{children}</button>,
}))
vi.mock('@/components/ui/badge', () => ({
    Badge: ({ children, ...props }) => <span {...props}>{children}</span>,
}))
vi.mock('lucide-react', () => ({
    RefreshCw: (props) => <span {...props} />,
    AlertCircle: (props) => <span {...props} />,
    Loader2: (props) => <span {...props} />,
}))

import ProjectList from './ProjectList'
import { useAdminProjects } from '../../hooks/useAdminProjects'

describe('ProjectList', () => {
    it('renders project count badges', () => {
        render(<ProjectList />)
        expect(screen.getByText('1 demo')).toBeInTheDocument()
        expect(screen.getByText('1 hyperobject')).toBeInTheDocument()
        expect(screen.getByText('3 total')).toBeInTheDocument()
    })

    it('renders a row for each project in the table', () => {
        render(<ProjectList />)
        expect(screen.getByTestId('flags-row-gridfinity')).toBeInTheDocument()
        expect(screen.getByTestId('flags-row-din-rail-clip')).toBeInTheDocument()
        expect(screen.getByTestId('flags-row-voronoi')).toBeInTheDocument()
    })

    it('shows loading state', () => {
        useAdminProjects.mockReturnValueOnce({
            projects: [], loading: true, error: null, refresh: mockRefresh, patchFlags: mockPatchFlags,
        })
        render(<ProjectList />)
        expect(screen.getByText(/loading projects/i)).toBeInTheDocument()
    })

    it('shows error state with retry button', () => {
        useAdminProjects.mockReturnValueOnce({
            projects: [], loading: false, error: 'Network failure', refresh: mockRefresh, patchFlags: mockPatchFlags,
        })
        render(<ProjectList />)
        expect(screen.getByText(/failed to load/i)).toBeInTheDocument()
        expect(screen.getByText(/network failure/i)).toBeInTheDocument()

        fireEvent.click(screen.getByText('Retry'))
        expect(mockRefresh).toHaveBeenCalled()
    })

    it('calls refresh when refresh button clicked', () => {
        render(<ProjectList />)
        fireEvent.click(screen.getByTitle('Refresh'))
        expect(mockRefresh).toHaveBeenCalled()
    })

    it('renders mobile card view', () => {
        render(<ProjectList />)
        // Mobile card view is a div with sm:hidden class
        // Check that project names appear (cards show name || slug)
        expect(screen.getAllByText('Gridfinity Extended').length).toBeGreaterThan(0)
    })

    it('renders explanatory text about demo and hyperobject', () => {
        render(<ProjectList />)
        // Text split across <strong> tags — use substring matching
        expect(screen.getByText(/projects appear in the landing/i)).toBeInTheDocument()
        expect(screen.getByText(/projects expose CDG/i)).toBeInTheDocument()
    })
})
