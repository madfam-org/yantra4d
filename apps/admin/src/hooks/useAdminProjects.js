/**
 * useAdminProjects — fetch and mutate project list via /api/admin/projects.
 *
 * Provides:
 *   projects       — array of enriched project objects
 *   loading        — boolean
 *   error          — string | null
 *   refresh()      — re-fetch
 *   patchFlags(slug, flags) — PATCH /api/admin/projects/<slug>/flags
 */
import { useState, useEffect, useCallback } from 'react'

function authHeaders() {
    const token = sessionStorage.getItem('janua_access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
}

export function useAdminProjects() {
    const [projects, setProjects] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const fetchProjects = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch('/api/admin/projects', {
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
            })
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            const data = await res.json()
            setProjects(data)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { fetchProjects() }, [fetchProjects])

    const patchFlags = useCallback(async (slug, flags) => {
        const res = await fetch(`/api/admin/projects/${slug}/flags`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
            body: JSON.stringify(flags),
        })
        if (!res.ok) {
            const body = await res.json().catch(() => ({}))
            throw new Error(body.error || `HTTP ${res.status}`)
        }
        const updated = await res.json()
        // Optimistically update local state
        setProjects(prev =>
            prev.map(p =>
                p.slug === slug ? { ...p, ...updated.updated } : p
            )
        )
        return updated
    }, [])

    return { projects, loading, error, refresh: fetchProjects, patchFlags }
}
