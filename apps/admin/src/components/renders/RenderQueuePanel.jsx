import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, AlertCircle, Loader2, Cpu, Info } from 'lucide-react'

function authHeaders() {
    const token = sessionStorage.getItem('janua_access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
}

export default function RenderQueuePanel() {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const fetchRenders = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch('/api/admin/renders/active', {
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
            })
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            setData(await res.json())
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { fetchRenders() }, [fetchRenders])

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin" />
                <p className="text-sm">Loading render status...</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-destructive">
                <AlertCircle className="h-6 w-6" />
                <p className="text-sm">Failed to load render status: {error}</p>
                <Button variant="outline" size="sm" onClick={fetchRenders}>Retry</Button>
            </div>
        )
    }

    if (!data) return null

    return (
        <div className="space-y-6">
            {/* Toolbar */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Badge variant={data.active_renders > 0 ? 'default' : 'secondary'}>
                        {data.active_renders} active
                    </Badge>
                </div>
                <Button variant="ghost" size="icon" onClick={fetchRenders} title="Refresh">
                    <RefreshCw className="h-4 w-4" />
                </Button>
            </div>

            {/* Active render count */}
            <div className="rounded-lg border border-border bg-card p-6">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted">
                        <Cpu className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div>
                        <p className="text-2xl font-bold tabular-nums">{data.active_renders}</p>
                        <p className="text-xs text-muted-foreground">Active renders right now</p>
                    </div>
                </div>
            </div>

            {/* Recent renders or empty state */}
            {data.recent && data.recent.length > 0 ? (
                <div className="space-y-3">
                    <h2 className="text-sm font-semibold text-foreground">Recent Renders</h2>
                    <div className="rounded-lg border border-border overflow-hidden">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-border bg-muted/50">
                                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Project</th>
                                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Mode</th>
                                    <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">Duration</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.recent.map((render, i) => (
                                    <tr
                                        key={i}
                                        className={`transition-colors hover:bg-muted/30 ${i < data.recent.length - 1 ? 'border-b border-border' : ''}`}
                                    >
                                        <td className="px-4 py-2.5 font-mono text-sm">{render.project}</td>
                                        <td className="px-4 py-2.5 text-muted-foreground">{render.mode}</td>
                                        <td className="px-4 py-2.5 text-right tabular-nums text-muted-foreground">{render.duration_ms}ms</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center gap-3 py-12 text-muted-foreground">
                    <Cpu className="h-8 w-8" />
                    <p className="text-sm">No active renders at the moment.</p>
                </div>
            )}

            {/* Integration note */}
            {data.note && (
                <div className="flex items-start gap-2.5 rounded-md border border-blue-500/30 bg-blue-500/10 px-3 py-2.5 text-blue-600 dark:text-blue-400">
                    <Info className="mt-0.5 h-4 w-4 shrink-0" />
                    <p className="text-xs leading-relaxed">{data.note}</p>
                </div>
            )}
        </div>
    )
}
