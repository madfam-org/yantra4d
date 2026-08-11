import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'

// In test environment, VITE_AUTH_ENABLED is not set, so the dev bypass activates
vi.mock('@janua/react-sdk', () => ({
    useAuth: vi.fn(() => ({
        user: null,
        isLoading: false,
        signIn: vi.fn(),
        signOut: vi.fn(),
    })),
}))

import { useJanuaAuth } from './useJanuaAuth'

describe('useJanuaAuth', () => {
    it('returns dev user when auth is not enabled', () => {
        const { result } = renderHook(() => useJanuaAuth())

        expect(result.current.isAuthenticated).toBe(true)
        expect(result.current.isLoading).toBe(false)
        expect(result.current.user).toEqual({
            id: 'dev-local',
            email: 'dev@local',
            roles: ['admin'],
            name: 'Local Dev Admin',
        })
    })

    it('provides signIn and signOut functions', () => {
        const { result } = renderHook(() => useJanuaAuth())

        expect(typeof result.current.signIn).toBe('function')
        expect(typeof result.current.signOut).toBe('function')
    })

    it('dev user has admin role', () => {
        const { result } = renderHook(() => useJanuaAuth())
        expect(result.current.user.roles).toContain('admin')
    })

    it('exposes inert auth actions in the dev bypass', async () => {
        const { result } = renderHook(() => useJanuaAuth())
        // The bypass has to satisfy the same shape as the real hook, so every
        // action must exist and resolve rather than throw.
        await expect(result.current.signIn()).resolves.toBeUndefined()
        await expect(result.current.signOut()).resolves.toBeUndefined()
        await expect(result.current.signInWithOAuth()).resolves.toBeUndefined()
        await expect(result.current.handleOAuthCallback()).resolves.toBeUndefined()
        expect(result.current.clearError()).toBeUndefined()
        expect(result.current.error).toBeNull()
    })
})

describe('useJanuaAuth with auth enabled', () => {
    // AUTH_ENABLED is captured at module load from import.meta.env, so the
    // production path only exists in a freshly imported module.
    beforeEach(() => {
        vi.resetModules()
        vi.stubEnv('VITE_AUTH_ENABLED', 'true')
    })
    afterEach(() => {
        vi.unstubAllEnvs()
        vi.resetModules()
    })

    async function loadWith(authState) {
        vi.doMock('@janua/react-sdk', () => ({ useAuth: () => authState }))
        const mod = await import('./useJanuaAuth')
        return mod
    }

    it('delegates to the SDK hook', async () => {
        const signIn = vi.fn()
        const { useJanuaAuth: hook, AUTH_ENABLED } = await loadWith({
            user: { id: 'u1', email: 'real@madfam.io' },
            isAuthenticated: true,
            isLoading: false,
            error: null,
            signIn,
            signOut: vi.fn(),
            signInWithOAuth: vi.fn(),
            handleOAuthCallback: vi.fn(),
            clearError: vi.fn(),
        })

        expect(AUTH_ENABLED).toBe(true)
        const { result } = renderHook(() => hook())
        expect(result.current.user).toEqual({ id: 'u1', email: 'real@madfam.io' })
        expect(result.current.isAuthenticated).toBe(true)
        expect(result.current.signIn).toBe(signIn)
    })

    it('normalises an undefined SDK user to null', async () => {
        const { useJanuaAuth: hook } = await loadWith({
            user: undefined,
            isAuthenticated: false,
            isLoading: true,
            error: 'boom',
            signIn: vi.fn(),
            signOut: vi.fn(),
            signInWithOAuth: vi.fn(),
            handleOAuthCallback: vi.fn(),
            clearError: vi.fn(),
        })

        const { result } = renderHook(() => hook())
        expect(result.current.user).toBeNull()
        expect(result.current.isLoading).toBe(true)
        expect(result.current.error).toBe('boom')
    })
})
