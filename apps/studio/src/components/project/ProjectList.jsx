import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ExternalLink } from "lucide-react"

export function ProjectList({ projects, t }) {
    if (!projects || projects.length === 0) return null

    return (
        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="w-[80px]">{t('projects.list.thumbnail') || 'Image'}</TableHead>
                        <TableHead>{t('projects.list.name') || 'Name'}</TableHead>
                        <TableHead>{t('projects.list.type') || 'Type'}</TableHead>
                        <TableHead>{t('projects.list.stats') || 'Stats'}</TableHead>
                        <TableHead className="text-right">{t('projects.list.updated') || 'Updated'}</TableHead>
                        <TableHead className="w-[50px]"></TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {projects.map((project) => (
                        <TableRow key={project.slug}>
                            <TableCell>
                                {project.thumbnail ? (
                                    <img
                                        src={project.thumbnail}
                                        alt={project.name}
                                        className="h-10 w-16 object-cover rounded bg-muted"
                                        loading="lazy"
                                    />
                                ) : (
                                    <div className="h-10 w-16 bg-muted rounded flex items-center justify-center text-xs text-muted-foreground">
                                        No Img
                                    </div>
                                )}
                            </TableCell>
                            <TableCell>
                                <div className="flex flex-col">
                                    <span className="font-medium">{project.name}</span>
                                    <span className="text-xs text-muted-foreground">{project.slug}</span>
                                </div>
                            </TableCell>
                            <TableCell>
                                <div className="flex gap-1 flex-wrap">
                                    {project.is_hyperobject && <Badge variant="outline" className="text-[10px] px-1 py-0 border-purple-500 text-purple-600">Hyperobject</Badge>}
                                    {project.is_demo && <Badge variant="outline" className="text-[10px] px-1 py-0 border-blue-500 text-blue-600">Demo</Badge>}
                                    {project.difficulty && (
                                        <Badge variant="secondary" className="text-[10px] px-1 py-0">
                                            {project.difficulty}
                                        </Badge>
                                    )}
                                </div>
                            </TableCell>
                            <TableCell>
                                <div className="flex flex-col text-xs text-muted-foreground">
                                    <span>{project.mode_count} modes</span>
                                    <span>{project.parameter_count} params</span>
                                </div>
                            </TableCell>
                            <TableCell className="text-right text-xs text-muted-foreground">
                                {project.modified_at ? new Date(project.modified_at * 1000).toLocaleDateString() : '-'}
                            </TableCell>
                            <TableCell>
                                <a href={`#/${project.slug}`}>
                                    <Button variant="ghost" size="icon" title={t('projects.open') || 'Open Project'}>
                                        <ExternalLink className="h-4 w-4" />
                                    </Button>
                                </a>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    )
}
