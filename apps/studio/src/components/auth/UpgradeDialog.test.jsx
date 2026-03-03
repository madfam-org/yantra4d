import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock LanguageProvider
vi.mock('../../contexts/system/LanguageProvider', () => ({
    useLanguage: () => ({
        t: (key) => {
            const map = {
                'tier.upgrade_title': 'Unlock Limitless Creation',
                'tier.upgrade_desc_1': "You've discovered a Pro feature!",
                'tier.upgrade_desc_2': 'Upgrade your plan to access:',
                'tier.maybe_later': 'Maybe Later',
                'tier.upgrade_button': 'Upgrade to Pro',
            }
            return map[key] || key
        },
    }),
}))

// Mock shadcn AlertDialog components
vi.mock('../ui/alert-dialog', () => ({
    AlertDialog: ({ children, open }) => open ? <div data-testid="alert-dialog">{children}</div> : null,
    AlertDialogContent: ({ children, ...props }) => <div {...props}>{children}</div>,
    AlertDialogHeader: ({ children }) => <div>{children}</div>,
    AlertDialogTitle: ({ children, ...props }) => <h2 {...props}>{children}</h2>,
    AlertDialogDescription: ({ children, ...props }) => <p {...props}>{children}</p>,
    AlertDialogFooter: ({ children, ...props }) => <div {...props}>{children}</div>,
    AlertDialogCancel: ({ children, onClick, ...props }) => (
        <button onClick={onClick} {...props}>{children}</button>
    ),
}))

import UpgradeDialog from './UpgradeDialog'

describe('UpgradeDialog', () => {
    const defaultProps = {
        isOpen: true,
        onClose: vi.fn(),
        feature: 'AI Code Editor',
    }

    it('renders when open', () => {
        render(<UpgradeDialog {...defaultProps} />)
        expect(screen.getByText('Unlock Limitless Creation')).toBeInTheDocument()
    })

    it('does not render when closed', () => {
        render(<UpgradeDialog {...defaultProps} isOpen={false} />)
        expect(screen.queryByText('Unlock Limitless Creation')).not.toBeInTheDocument()
    })

    it('displays the feature name', () => {
        render(<UpgradeDialog {...defaultProps} />)
        expect(screen.getByText('AI Code Editor')).toBeInTheDocument()
    })

    it('shows upgrade description text', () => {
        render(<UpgradeDialog {...defaultProps} />)
        expect(screen.getByText(/discovered a Pro feature/)).toBeInTheDocument()
    })

    it('calls onClose when Maybe Later is clicked', () => {
        const onClose = vi.fn()
        render(<UpgradeDialog {...defaultProps} onClose={onClose} />)
        fireEvent.click(screen.getByText('Maybe Later'))
        expect(onClose).toHaveBeenCalled()
    })

    it('has an upgrade link to pricing page', () => {
        render(<UpgradeDialog {...defaultProps} />)
        const link = screen.getByText('Upgrade to Pro')
        expect(link.closest('a')).toHaveAttribute('href', 'https://4d.madfam.io/#pricing')
        expect(link.closest('a')).toHaveAttribute('target', '_blank')
    })
})
