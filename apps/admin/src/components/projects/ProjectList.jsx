import { useAdminProjects } from '../../hooks/useAdminProjects'
import ProjectFlagsRow from './ProjectFlagsRow'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, AlertCircle, Loader2 } from 'lucide-react'

export default function ProjectList() {
    const { projects, loading, error, refresh } = useAdminProjects()

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin" />
                <p className="text-sm">Loading projects…</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-destructive">
                <AlertCircle className="h-6 w-6" />
                <p className="text-sm">Failed to load projects: {error}</p>
                <Button variant="outline" size="sm" onClick={refresh}>Retry</Button>
            </div>
        )
    }

    const demoCount = projects.filter(p => p.is_demo).length
    const hyperobjectCount = projects.filter(p => p.is_hyperobject).length

    return (
        <div className="space-y-4">
            {/* Toolbar */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-amber-500 border-amber-500/40 bg-amber-500/10">
                        {demoCount} demo
                    </Badge>
                    <Badge variant="outline" className="text-violet-500 border-violet-500/40 bg-violet-500/10">
                        {hyperobjectCount} hyperobject
                    </Badge>
                    <Badge variant="secondary">{projects.length} total</Badge>
                </div>
                <Button variant="ghost" size="icon" onClick={refresh} title="Refresh">
                    <RefreshCw className="h-4 w-4" />
                </Button>
            </div>

            {/* Table */}
            <div className="rounded-lg border border-border overflow-hidden">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-border bg-muted/50">
                            <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Project</th>
                            <th className="px-4 py-2.5 text-center text-xs font-semibold uppercase tracking-wide text-muted-foreground">Demo</th>
                            <th className="px-4 py-2.5 text-center text-xs font-semibold uppercase tracking-wide text-muted-foreground">Hyperobject</th>
                            <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">Modes</th>
                            <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">Params</th>
                        </tr>
                    </thead>
                    <tbody>
                        {projects.map((project, i) => (
                            <ProjectFlagsRow
                                key={project.slug}
                                project={project}
                                isLast={i === projects.length - 1}
                            />
                        ))}
                    </tbody>
                </table>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Demo</strong> projects appear in the landing page gallery and studio quick-start.{' '}
                <strong className="text-foreground">Hyperobject</strong> projects expose CDG interfaces for parametric composition.
            </p>
        </div>
    )
}
