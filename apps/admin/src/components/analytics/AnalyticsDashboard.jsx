import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, AlertCircle, Loader2, BarChart3, Download, Activity } from 'lucide-react'

function authHeaders() {
    const token = sessionStorage.getItem('janua_access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
}

export default function AnalyticsDashboard() {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const fetchAnalytics = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch('/api/admin/analytics/global?days=30', {
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

    useEffect(() => { fetchAnalytics() }, [fetchAnalytics])

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin" />
                <p className="text-sm">Loading analytics...</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-destructive">
                <AlertCircle className="h-6 w-6" />
                <p className="text-sm">Failed to load analytics: {error}</p>
                <Button variant="outline" size="sm" onClick={fetchAnalytics}>Retry</Button>
            </div>
        )
    }

    if (!data) return null

    return (
        <div className="space-y-6">
            {/* Toolbar */}
            <div className="flex items-center justify-between">
                <Badge variant="secondary">Last {data.period_days} days</Badge>
                <Button variant="ghost" size="icon" onClick={fetchAnalytics} title="Refresh">
                    <RefreshCw className="h-4 w-4" />
                </Button>
            </div>

            {/* Metric cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <MetricCard
                    icon={BarChart3}
                    label="Total Renders"
                    value={data.total_renders}
                    color="text-blue-500"
                    bgColor="bg-blue-500/10"
                />
                <MetricCard
                    icon={Download}
                    label="Total Exports"
                    value={data.total_exports}
                    color="text-green-500"
                    bgColor="bg-green-500/10"
                />
                <MetricCard
                    icon={Activity}
                    label="Total Events"
                    value={data.total_events}
                    color="text-violet-500"
                    bgColor="bg-violet-500/10"
                />
            </div>

            {/* Top projects */}
            {data.top_projects.length > 0 && (
                <div className="space-y-3">
                    <h2 className="text-sm font-semibold text-foreground">Top Projects by Renders</h2>
                    <div className="rounded-lg border border-border overflow-hidden">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-border bg-muted/50">
                                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Project</th>
                                    <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">Renders</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.top_projects.slice(0, 5).map((proj, i) => (
                                    <tr
                                        key={proj.slug}
                                        className={`transition-colors hover:bg-muted/30 ${i < data.top_projects.slice(0, 5).length - 1 ? 'border-b border-border' : ''}`}
                                    >
                                        <td className="px-4 py-2.5">
                                            <code className="font-mono text-sm">{proj.slug}</code>
                                        </td>
                                        <td className="px-4 py-2.5 text-right tabular-nums text-muted-foreground">{proj.renders}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Daily renders table */}
            {data.daily_renders.length > 0 && (
                <div className="space-y-3">
                    <h2 className="text-sm font-semibold text-foreground">Daily Renders</h2>
                    <div className="rounded-lg border border-border overflow-hidden max-h-[400px] overflow-y-auto">
                        <table className="w-full text-sm">
                            <thead className="sticky top-0">
                                <tr className="border-b border-border bg-muted/50">
                                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Date</th>
                                    <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">Renders</th>
                                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Bar</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.daily_renders.map((day, i) => {
                                    const maxCount = Math.max(...data.daily_renders.map(d => d.count), 1)
                                    const barWidth = Math.round((day.count / maxCount) * 100)
                                    return (
                                        <tr
                                            key={day.date}
                                            className={`transition-colors hover:bg-muted/30 ${i < data.daily_renders.length - 1 ? 'border-b border-border' : ''}`}
                                        >
                                            <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{day.date}</td>
                                            <td className="px-4 py-2 text-right tabular-nums text-sm">{day.count}</td>
                                            <td className="px-4 py-2">
                                                <div className="h-3 w-full max-w-[200px] rounded-full bg-muted">
                                                    <div
                                                        className="h-3 rounded-full bg-blue-500/70"
                                                        style={{ width: `${barWidth}%` }}
                                                    />
                                                </div>
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {data.daily_renders.length === 0 && data.top_projects.length === 0 && (
                <div className="flex flex-col items-center justify-center gap-2 py-12 text-muted-foreground">
                    <BarChart3 className="h-8 w-8" />
                    <p className="text-sm">No analytics events recorded in the last {data.period_days} days.</p>
                </div>
            )}

            {/* Event type breakdown */}
            {data.event_counts && Object.keys(data.event_counts).length > 0 && (
                <div className="space-y-3">
                    <h2 className="text-sm font-semibold text-foreground">Event Breakdown</h2>
                    <div className="flex flex-wrap gap-2">
                        {Object.entries(data.event_counts)
                            .sort(([, a], [, b]) => b - a)
                            .map(([type, count]) => (
                                <Badge key={type} variant="outline" className="text-xs">
                                    {type}: {count}
                                </Badge>
                            ))}
                    </div>
                </div>
            )}
        </div>
    )
}

function MetricCard({ icon: Icon, label, value, color, bgColor }) {
    return (
        <div className="rounded-lg border border-border bg-card p-4 space-y-2">
            <div className="flex items-center gap-2">
                <div className={`flex h-8 w-8 items-center justify-center rounded-md ${bgColor}`}>
                    <Icon className={`h-4 w-4 ${color}`} />
                </div>
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</span>
            </div>
            <p className="text-2xl font-bold tabular-nums">{value.toLocaleString()}</p>
        </div>
    )
}
