import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock child components
vi.mock('./projects/ProjectList', () => ({
    default: () => <div data-testid="project-list">ProjectList</div>,
}))
vi.mock('./projects/TablacoLinkPanel', () => ({
    default: () => <div data-testid="tablaco-link-panel">TablacoLinkPanel</div>,
}))

// Mock Janua SDK
vi.mock('@janua/react-sdk', () => ({
    UserProfile: () => <div data-testid="user-profile">User</div>,
}))

// Mock Shadcn UI
vi.mock('@/components/ui/button', () => ({
    Button: ({ children, ...props }) => <button {...props}>{children}</button>,
}))
vi.mock('@/components/ui/badge', () => ({
    Badge: ({ children, ...props }) => <span data-testid="badge" {...props}>{children}</span>,
}))

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
    LayoutDashboard: (props) => <span {...props} />,
    ExternalLink: (props) => <span {...props} />,
    Menu: (props) => <span {...props} />,
    X: (props) => <span {...props} />,
}))

import AdminShell from './AdminShell'

describe('AdminShell', () => {
    const defaultAuth = {
        user: { name: 'Admin User', email: 'admin@test.com' },
        isAuthenticated: true,
        isLoading: false,
    }

    it('renders without crash', () => {
        render(<AdminShell auth={defaultAuth} />)
        expect(screen.getAllByText('Projects').length).toBeGreaterThan(0)
    })

    it('shows project list by default', () => {
        render(<AdminShell auth={defaultAuth} />)
        expect(screen.getByTestId('project-list')).toBeInTheDocument()
    })

    it('switches to tablaco link panel when nav item clicked', () => {
        render(<AdminShell auth={defaultAuth} />)
        fireEvent.click(screen.getByText('Tablaco Link'))
        expect(screen.getByTestId('tablaco-link-panel')).toBeInTheDocument()
    })

    it('switches back to projects view', () => {
        render(<AdminShell auth={defaultAuth} />)
        fireEvent.click(screen.getByText('Tablaco Link'))
        expect(screen.getByTestId('tablaco-link-panel')).toBeInTheDocument()

        // Switch back — both sidebar nav button and header h1 show "Projects"
        const projectsButtons = screen.getAllByText('Projects')
        // Click the nav button (not the h1)
        fireEvent.click(projectsButtons[0])
        expect(screen.getByTestId('project-list')).toBeInTheDocument()
    })

    it('displays user email', () => {
        render(<AdminShell auth={defaultAuth} />)
        expect(screen.getByText('admin@test.com')).toBeInTheDocument()
    })

    it('shows Local Dev badge when auth not enabled', () => {
        render(<AdminShell auth={defaultAuth} />)
        expect(screen.getByText('Local Dev')).toBeInTheDocument()
    })

    it('renders sidebar brand', () => {
        render(<AdminShell auth={defaultAuth} />)
        expect(screen.getByText('Y4D')).toBeInTheDocument()
        expect(screen.getByText('Admin')).toBeInTheDocument()
    })

    it('renders UserProfile component', () => {
        render(<AdminShell auth={defaultAuth} />)
        expect(screen.getByTestId('user-profile')).toBeInTheDocument()
    })

    it('highlights active nav item with aria-current', () => {
        render(<AdminShell auth={defaultAuth} />)
        const projectsNav = screen.getAllByText('Projects')[0]
        expect(projectsNav).toHaveAttribute('aria-current', 'page')
    })

    it('opens sidebar on mobile menu button click', () => {
        render(<AdminShell auth={defaultAuth} />)
        const menuBtn = screen.getByRole('button', { name: /open sidebar/i })
        fireEvent.click(menuBtn)
        // Sidebar should now be visible (translate-x-0)
        // Backdrop should appear
        const backdrop = document.querySelector('.bg-black\\/40')
        expect(backdrop).toBeInTheDocument()
    })
})
