import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

// Mock fetch globally
const mockFetch = vi.fn()
globalThis.fetch = mockFetch

import PrintPanel from './PrintPanel'

const MOCK_PRINTERS = [
    { id: 'printer-one', name: 'Printer One', model: 'X1', connection_type: 'octoprint' },
    { id: 'printer-two', name: 'Printer Two', model: 'K2', connection_type: 'moonraker' },
]

const MOCK_STATUS = {
    printer_id: 'printer-one',
    name: 'Printer One',
    state: 'Operational',
    temperatures: {
        tool0: { actual: 25.0, target: 0 },
        bed: { actual: 22.5, target: 0 },
    },
    job: null,
}

describe('PrintPanel', () => {
    const defaultProps = {
        currentPartUrls: ['/static/preview_main.glb'],
        tier: 'pro',
    }

    beforeEach(() => {
        vi.clearAllMocks()
        mockFetch.mockReset()
    })

    it('renders null when no printers available', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ printers: [] }),
        })

        const { container } = render(<PrintPanel {...defaultProps} />)
        await waitFor(() => {
            expect(container.innerHTML).toBe('')
        })
    })

    it('renders printer panel when printers exist', async () => {
        mockFetch
            .mockResolvedValueOnce({ ok: true, json: async () => ({ printers: MOCK_PRINTERS }) })
            .mockResolvedValueOnce({ ok: true, json: async () => MOCK_STATUS })

        render(<PrintPanel {...defaultProps} />)

        await waitFor(() => {
            expect(screen.getByRole('region', { name: 'Print Panel' })).toBeInTheDocument()
        })
    })

    it('shows printer selector when multiple printers exist', async () => {
        mockFetch
            .mockResolvedValueOnce({ ok: true, json: async () => ({ printers: MOCK_PRINTERS }) })
            .mockResolvedValueOnce({ ok: true, json: async () => MOCK_STATUS })

        render(<PrintPanel {...defaultProps} />)

        await waitFor(() => {
            // Printer select may be a <select> element
            const select = screen.getByRole('combobox')
            expect(select).toBeInTheDocument()
        })
    })

    it('shows upgrade message for guest tier', async () => {
        mockFetch
            .mockResolvedValueOnce({ ok: true, json: async () => ({ printers: MOCK_PRINTERS }) })
            .mockResolvedValueOnce({ ok: true, json: async () => MOCK_STATUS })

        render(<PrintPanel currentPartUrls={['/static/test.glb']} tier="guest" />)

        await waitFor(() => {
            expect(screen.getByText(/Print dispatch requires/)).toBeInTheDocument()
            expect(screen.getByText('Pro')).toBeInTheDocument()
        })
    })

    it('shows send button for pro tier', async () => {
        mockFetch
            .mockResolvedValueOnce({ ok: true, json: async () => ({ printers: MOCK_PRINTERS }) })
            .mockResolvedValueOnce({ ok: true, json: async () => MOCK_STATUS })

        render(<PrintPanel {...defaultProps} />)

        await waitFor(() => {
            expect(screen.getByText('Send to Printer')).toBeInTheDocument()
        })
    })

    it('disables send button when no parts rendered', async () => {
        mockFetch
            .mockResolvedValueOnce({ ok: true, json: async () => ({ printers: MOCK_PRINTERS }) })
            .mockResolvedValueOnce({ ok: true, json: async () => MOCK_STATUS })

        render(<PrintPanel currentPartUrls={[]} tier="pro" />)

        await waitFor(() => {
            const btn = screen.getByText('Send to Printer')
            expect(btn).toBeDisabled()
        })
    })

    it('displays temperature gauges', async () => {
        mockFetch
            .mockResolvedValueOnce({ ok: true, json: async () => ({ printers: MOCK_PRINTERS }) })
            .mockResolvedValueOnce({ ok: true, json: async () => MOCK_STATUS })

        render(<PrintPanel {...defaultProps} />)

        await waitFor(() => {
            expect(screen.getByText(/Nozzle/)).toBeInTheDocument()
            expect(screen.getByText(/25\.0/)).toBeInTheDocument()
        })
    })

    it('shows cancel button when printing', async () => {
        const printingStatus = {
            ...MOCK_STATUS,
            state: 'Printing',
            job: { file: 'test.stl', progress_pct: 45.2, time_remaining_s: 120 },
        }
        mockFetch
            .mockResolvedValueOnce({ ok: true, json: async () => ({ printers: MOCK_PRINTERS }) })
            .mockResolvedValueOnce({ ok: true, json: async () => printingStatus })

        render(<PrintPanel {...defaultProps} />)

        await waitFor(() => {
            expect(screen.getByText('Cancel Print')).toBeInTheDocument()
            expect(screen.getByText(/45\.2%/)).toBeInTheDocument()
        })
    })

    it('handles fetch printers failure gracefully', async () => {
        mockFetch.mockRejectedValueOnce(new Error('Network error'))

        const { container } = render(<PrintPanel {...defaultProps} />)
        await waitFor(() => {
            expect(container.innerHTML).toBe('')
        })
    })
})
