import { describe, it, expect, vi } from 'vitest'
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
})
