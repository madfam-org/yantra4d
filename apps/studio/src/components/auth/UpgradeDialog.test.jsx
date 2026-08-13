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

// Mock auth — the dialog reads user.id for the checkout URL.
vi.mock('../../contexts/auth/AuthProvider', () => ({
    useAuth: () => ({ user: { id: 'user-42' } }),
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

    it('the Upgrade CTA is the checkout link, not the old pricing anchor', () => {
        render(<UpgradeDialog {...defaultProps} />)
        const link = screen.getByText('Upgrade to Pro')
        // Repurposed from the pre-billing behavior this file used to pin: the
        // primary CTA now goes to checkout; the pricing page is the secondary.
        expect(link.closest('a').getAttribute('href')).toContain('/checkout')
    })

    it('primary CTA links to Dhanam checkout with the user and a return URL', () => {
        render(<UpgradeDialog {...defaultProps} />)
        const link = screen.getByTestId('upgrade-checkout-link')
        const href = link.getAttribute('href')
        // The dead-end this guards: the CTA used to point at a #pricing anchor
        // that did not exist, and the real checkout builder had no callers.
        expect(href).toContain('/checkout')
        expect(href).toContain('plan=yantra4d_pro')
        expect(href).toContain('product=yantra4d')
        expect(href).toContain('user_id=user-42')
        expect(href).toContain('return_url=')
    })

    it('shows the plan price and closes on checkout click', () => {
        const onClose = vi.fn()
        render(<UpgradeDialog {...defaultProps} onClose={onClose} />)
        expect(screen.getByText(/from \$9\/mo|tier\.pro_price/)).toBeInTheDocument()
        fireEvent.click(screen.getByTestId('upgrade-checkout-link'))
        expect(onClose).toHaveBeenCalled()
    })

    it('keeps a secondary link to the public pricing page', () => {
        render(<UpgradeDialog {...defaultProps} />)
        const links = [...document.querySelectorAll('a')].map(a => a.getAttribute('href'))
        expect(links).toContain('https://yantra4d.com/#pricing')
    })
})

