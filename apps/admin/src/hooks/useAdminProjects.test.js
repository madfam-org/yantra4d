import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useAdminProjects } from './useAdminProjects'

describe('useAdminProjects', () => {
    beforeEach(() => {
        vi.restoreAllMocks()
        sessionStorage.clear()
    })

    it('fetches projects on mount', async () => {
        const mockProjects = [
            { slug: 'gridfinity', is_demo: true, is_hyperobject: false },
        ]
        globalThis.fetch = vi.fn().mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve(mockProjects),
        })

        const { result } = renderHook(() => useAdminProjects())

        await waitFor(() => {
            expect(result.current.loading).toBe(false)
        })
        expect(result.current.projects).toEqual(mockProjects)
        expect(result.current.error).toBeNull()
    })

    it('sets error on fetch failure', async () => {
        globalThis.fetch = vi.fn().mockResolvedValueOnce({
            ok: false,
            status: 500,
        })

        const { result } = renderHook(() => useAdminProjects())

        await waitFor(() => {
            expect(result.current.loading).toBe(false)
        })
        expect(result.current.error).toBe('HTTP 500')
        expect(result.current.projects).toEqual([])
    })

    it('refresh re-fetches projects', async () => {
        globalThis.fetch = vi.fn()
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([{ slug: 'new-project' }]),
            })

        const { result } = renderHook(() => useAdminProjects())

        await waitFor(() => expect(result.current.loading).toBe(false))
        expect(result.current.projects).toEqual([])

        await act(async () => {
            await result.current.refresh()
        })

        expect(result.current.projects).toEqual([{ slug: 'new-project' }])
    })

    it('patchFlags sends PATCH request', async () => {
        globalThis.fetch = vi.fn()
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve([{ slug: 'test', is_demo: false }]),
            })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ updated: { is_demo: true } }),
            })

        const { result } = renderHook(() => useAdminProjects())

        await waitFor(() => expect(result.current.loading).toBe(false))

        await act(async () => {
            await result.current.patchFlags('test', { is_demo: true })
        })

        expect(globalThis.fetch).toHaveBeenLastCalledWith(
            '/api/admin/projects/test/flags',
            expect.objectContaining({
                method: 'PATCH',
                body: JSON.stringify({ is_demo: true }),
            })
        )
    })

    it('patchFlags throws on failure', async () => {
        globalThis.fetch = vi.fn()
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) })
            .mockResolvedValueOnce({
                ok: false,
                status: 403,
                json: () => Promise.resolve({ error: 'Forbidden' }),
            })

        const { result } = renderHook(() => useAdminProjects())
        await waitFor(() => expect(result.current.loading).toBe(false))

        await expect(
            act(() => result.current.patchFlags('test', { is_demo: true }))
        ).rejects.toThrow('Forbidden')
    })

    it('includes auth token in headers when available', async () => {
        sessionStorage.setItem('janua_access_token', 'test-token-123')
        globalThis.fetch = vi.fn().mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve([]),
        })

        renderHook(() => useAdminProjects())

        await waitFor(() => {
            expect(globalThis.fetch).toHaveBeenCalledWith(
                '/api/admin/projects',
                expect.objectContaining({
                    headers: expect.objectContaining({
                        Authorization: 'Bearer test-token-123',
                    }),
                })
            )
        })
    })
})
