import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, AlertCircle, Loader2, Users, Info, Shield } from 'lucide-react'

function authHeaders() {
    const token = sessionStorage.getItem('janua_access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
}

const TIER_COLORS = {
    guest: 'text-zinc-500 border-zinc-500/40 bg-zinc-500/10',
    basic: 'text-blue-500 border-blue-500/40 bg-blue-500/10',
    pro: 'text-amber-500 border-amber-500/40 bg-amber-500/10',
    madfam: 'text-violet-500 border-violet-500/40 bg-violet-500/10',
}

export default function UserOverview() {
    const [tiers, setTiers] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const fetchTiers = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch('/api/tiers', {
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
            })
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            setTiers(await res.json())
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { fetchTiers() }, [fetchTiers])

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin" />
                <p className="text-sm">Loading tier definitions...</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-destructive">
                <AlertCircle className="h-6 w-6" />
                <p className="text-sm">Failed to load tiers: {error}</p>
                <Button variant="outline" size="sm" onClick={fetchTiers}>Retry</Button>
            </div>
        )
    }

    if (!tiers) return null

    // tiers is either an object { guest: {...}, basic: {...} } or an array
    const tierEntries = Array.isArray(tiers) ? tiers : Object.entries(tiers)

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Users className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium text-muted-foreground">Tier Definitions</span>
                </div>
                <Button variant="ghost" size="icon" onClick={fetchTiers} title="Refresh">
                    <RefreshCw className="h-4 w-4" />
                </Button>
            </div>

            {/* Tier cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {(Array.isArray(tierEntries) ? tierEntries : []).map((entry) => {
                    // Handle both { name, ... } array entries and [key, value] entries
                    const [tierKey, tierData] = Array.isArray(entry) ? entry : [entry.name || entry.id, entry]
                    const colorClass = TIER_COLORS[tierKey] || 'text-zinc-500 border-zinc-500/40 bg-zinc-500/10'

                    return (
                        <div key={tierKey} className="rounded-lg border border-border bg-card p-4 space-y-3">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Shield className="h-4 w-4 text-muted-foreground" />
                                    <Badge variant="outline" className={`${colorClass} font-semibold`}>
                                        {tierKey}
                                    </Badge>
                                </div>
                            </div>

                            <div className="space-y-1.5 text-xs text-muted-foreground">
                                {(tierData.backend_renders_per_hour ?? tierData.renders_per_hour) != null && (
                                    <div className="flex justify-between">
                                        <span>Server renders/hr</span>
                                        <span className="font-mono tabular-nums">{tierData.backend_renders_per_hour ?? tierData.renders_per_hour}</span>
                                    </div>
                                )}
                                {tierData.max_projects != null && (
                                    <div className="flex justify-between">
                                        <span>Max projects</span>
                                        <span className="font-mono tabular-nums">
                                            {tierData.max_projects === -1 ? 'unlimited' : tierData.max_projects}
                                        </span>
                                    </div>
                                )}
                                {tierData.export_formats && (
                                    <div className="flex justify-between gap-2">
                                        <span className="shrink-0">Export formats</span>
                                        <span className="font-mono text-right truncate">
                                            {Array.isArray(tierData.export_formats)
                                                ? tierData.export_formats.join(', ')
                                                : tierData.export_formats}
                                        </span>
                                    </div>
                                )}
                                {tierData.ai_requests_per_hour != null && (
                                    <div className="flex justify-between">
                                        <span>AI requests/hr</span>
                                        <span className="font-mono tabular-nums">{tierData.ai_requests_per_hour}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    )
                })}
            </div>

            {/* Integration note */}
            <div className="flex items-start gap-2.5 rounded-md border border-blue-500/30 bg-blue-500/10 px-3 py-2.5 text-blue-600 dark:text-blue-400">
                <Info className="mt-0.5 h-4 w-4 shrink-0" />
                <p className="text-xs leading-relaxed">
                    Full user management requires Janua admin API integration. Tier assignments are managed
                    through Dhanam billing webhooks. This view shows the available tier definitions from the backend.
                </p>
            </div>
        </div>
    )
}
