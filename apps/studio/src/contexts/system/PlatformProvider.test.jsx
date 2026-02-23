import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { PlatformProvider, usePlatform } from './PlatformProvider'
import { apiFetch } from '../../services/core/apiClient'
import React from 'react'

vi.mock('../../services/core/apiClient')

describe('PlatformProvider', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('fetches and sets platform config from api successfully', async () => {
        apiFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ platformName: 'Custom4D', platformLogo: '/custom.png' })
        })

        const wrapper = ({ children }) => <PlatformProvider>{children}</PlatformProvider>
        const { result } = renderHook(() => usePlatform(), { wrapper })

        expect(result.current.loading).toBe(true)

        await waitFor(() => {
            expect(result.current.loading).toBe(false)
        })

        expect(result.current.platformName).toBe('Custom4D')
        expect(result.current.platformLogo).toBe('/custom.png')
    })

    it('falls back to defaults if api fetch fails', async () => {
        apiFetch.mockRejectedValueOnce(new Error('Network error'))
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

        const wrapper = ({ children }) => <PlatformProvider>{children}</PlatformProvider>
        const { result } = renderHook(() => usePlatform(), { wrapper })

        await waitFor(() => {
            expect(result.current.loading).toBe(false)
        })

        expect(result.current.platformName).toBe('Yantra4D')
        expect(result.current.platformLogo).toBe('/logo.png')
        warnSpy.mockRestore()
    })
})
