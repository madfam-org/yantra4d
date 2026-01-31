import { useState, useEffect } from 'react'
import { getApiBase } from '../services/backendDetection'
import { useLanguage } from '../contexts/LanguageProvider'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'

export default function ProjectsView() {
  const { t } = useLanguage()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch(`${getApiBase()}/api/admin/projects`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(data => {
        setProjects(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">{t('projects.loading')}</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-destructive">{t('projects.error')}{error}</p>
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-muted-foreground">{t('projects.empty')}</p>
        <a href="#/onboard" className="text-sm text-primary hover:underline">
          {t('projects.empty_cta')}
        </a>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">{t('projects.title')}</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {projects.map(project => (
          <a
            key={project.slug}
            href={`#/${project.slug}`}
            className="block hover:ring-2 hover:ring-ring rounded-lg transition-shadow"
          >
            <Card className="h-full flex flex-col">
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-lg">{project.name}</CardTitle>
                  <span className="text-xs text-muted-foreground shrink-0">v{project.version}</span>
                </div>
                {project.description && (
                  <CardDescription className="line-clamp-2">{project.description}</CardDescription>
                )}
              </CardHeader>
              <CardContent className="flex-1">
                <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground">
                  <span>{project.mode_count} mode{project.mode_count !== 1 ? 's' : ''}</span>
                  <span>·</span>
                  <span>{project.parameter_count} param{project.parameter_count !== 1 ? 's' : ''}</span>
                  <span>·</span>
                  <span>{project.scad_file_count} .scad</span>
                </div>
              </CardContent>
              <CardFooter className="gap-2 flex-wrap">
                {project.has_manifest && <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold text-muted-foreground">{t('projects.manifest')}</span>}
                {project.has_exports && <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold text-muted-foreground">{t('projects.exports')}</span>}
                {project.modified_at && (
                  <span className="text-xs text-muted-foreground ml-auto">
                    {new Date(project.modified_at * 1000).toLocaleDateString()}
                  </span>
                )}
              </CardFooter>
            </Card>
          </a>
        ))}
      </div>
    </div>
  )
}
