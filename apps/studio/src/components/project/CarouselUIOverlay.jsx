import { Link } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Settings2, ArrowRight } from 'lucide-react'

export default function CarouselUIOverlay({ project, loc, index, total }) {
    if (!project) return null

    return (
        <div className="absolute inset-0 pointer-events-none flex flex-col justify-between p-8">

            {/* Top Bar Navigation / Paginator */}
            <div className="flex justify-between items-start pointer-events-auto">
                <div className="bg-background/80 backdrop-blur-md px-4 py-2 rounded-full border border-border shadow-sm">
                    <span className="text-sm font-medium">
                        {index + 1} <span className="text-muted-foreground mr-1">/</span> {total}
                    </span>
                </div>
            </div>

            {/* Bottom Card Info Overlay */}
            <div className="w-full max-w-md pointer-events-auto mt-auto">
                <Card className="bg-background/80 backdrop-blur-xl border-border/50 shadow-2xl transition-all duration-300 transform translate-y-0 opacity-100">
                    <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-2xl font-bold tracking-tight">
                                {project.name}
                            </CardTitle>
                            {project.version && (
                                <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-semibold">
                                    v{project.version}
                                </span>
                            )}
                        </div>
                        <CardDescription className="text-base text-foreground/80 line-clamp-2 leading-relaxed">
                            {loc(project.description)}
                        </CardDescription>
                    </CardHeader>

                    <CardContent className="pb-4">
                        <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
                            <div className="flex items-center gap-1.5">
                                <Settings2 className="w-4 h-4" />
                                <span>{project.parameter_count || 0} Param{project.parameter_count !== 1 ? 's' : ''}</span>
                            </div>
                            {project.difficulty && (
                                <div className="capitalize font-medium">
                                    {project.difficulty}
                                </div>
                            )}
                        </div>

                        {/* Badges */}
                        <div className="flex flex-wrap gap-2">
                            {project.is_hyperobject && (
                                <span className="px-2.5 py-1 rounded border border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400 text-xs font-medium tracking-wide uppercase">
                                    Hyperobject
                                </span>
                            )}
                            {(project.tags || []).slice(0, 3).map(tag => (
                                <span key={tag} className="px-2 py-1 rounded bg-muted text-muted-foreground text-xs font-medium">
                                    {tag}
                                </span>
                            ))}
                        </div>
                    </CardContent>

                    <CardFooter className="pt-0 border-t border-border/40 mt-4 flex items-center justify-between">
                        <p className="text-xs text-muted-foreground italic">Live 3D Rendering Active</p>
                        <Link to={`/project/${project.slug}`}>
                            <Button className="gap-2 shrink-0 group">
                                Open Studio
                                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                            </Button>
                        </Link>
                    </CardFooter>
                </Card>
            </div>

        </div>
    )
}
