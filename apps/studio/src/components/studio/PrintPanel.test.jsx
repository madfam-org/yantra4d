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

    // --- Status, temperature, job progress and dispatch ----------------------
    // Only the empty-printer-list and happy-path render were covered. The
    // temperature gauges, active job, dispatch handler and every non-OK
    // response path were not.

    const withPrinters = (status = MOCK_STATUS) => {
        mockFetch
            .mockResolvedValueOnce({ ok: true, json: async () => ({ printers: MOCK_PRINTERS }) })
            .mockResolvedValue({ ok: true, json: async () => status })
    }

    const panel = async () => {
        render(<PrintPanel {...defaultProps} />)
        return screen.findByRole('region', { name: 'Print Panel' })
    }

    it('renders nothing when the printer list request fails', async () => {
        mockFetch.mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({}) })
        const { container } = render(<PrintPanel {...defaultProps} />)
        await waitFor(() => expect(container.innerHTML).toBe(''))
    })

    it('renders nothing when the printer list request throws', async () => {
        mockFetch.mockRejectedValueOnce(new Error('offline'))
        const { container } = render(<PrintPanel {...defaultProps} />)
        await waitFor(() => expect(container.innerHTML).toBe(''))
    })

    it('shows the reported printer state', async () => {
        withPrinters()
        await panel()
        expect(await screen.findByText(/Operational/)).toBeInTheDocument()
    })

    it('falls back to Unknown when the status carries no state', async () => {
        withPrinters({ ...MOCK_STATUS, state: undefined })
        await panel()
        expect(await screen.findByText(/Unknown/)).toBeInTheDocument()
    })

    it('temperature gauges show a reading, and an em dash when there is none', async () => {
        withPrinters({
            ...MOCK_STATUS,
            temperatures: { tool0: { actual: 210.4, target: 210 }, bed: { actual: null, target: 60 } },
        })
        await panel()
        expect(await screen.findByText(/210\.4°C/)).toBeInTheDocument()
        // A null reading must render as — rather than "null°C" or a crash.
        expect(screen.getByText(/—/)).toBeInTheDocument()
    })

    it('an active job renders its progress', async () => {
        withPrinters({
            ...MOCK_STATUS,
            state: 'Printing',
            job: { file: 'part.gcode', progress_pct: 42 },
        })
        await panel()
        expect(await screen.findByText(/42/)).toBeInTheDocument()
    })

    it('a job with no reported percentage does not break the progress bar', async () => {
        withPrinters({
            ...MOCK_STATUS,
            state: 'Printing',
            job: { file: 'part.gcode' },
        })
        await panel()
        expect(await screen.findByText(/part\.gcode/)).toBeInTheDocument()
    })
})

