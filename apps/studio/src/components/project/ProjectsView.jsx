import { useState, useEffect, useMemo, useCallback, lazy, Suspense } from 'react'
import { getApiBase } from '../../services/backendDetection'
import { useLanguage } from '../../contexts/LanguageProvider'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Github } from 'lucide-react'
import AuthGate from '../auth/AuthGate'
import { ProjectToolbar } from './ProjectToolbar'
import { ProjectList } from './ProjectList'

const GitHubImportWizard = lazy(() => import('../ai/GitHubImportWizard'))

const DIFFICULTY_COLORS = {
  beginner: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  intermediate: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  advanced: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
}

const getRenderSpeed = (constants) => {
  if (!constants) return null
  // Heuristic: base_time + (per_part * 5 parts)
  const score = constants.base_time + (constants.per_part * 5)
  if (score < 5) return { label: 'Fast Render', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' }
  if (score < 15) return { label: 'Medium Render', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' }
  return { label: 'Slow Render', color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' }
}

export default function ProjectsView() {
  const { t, language } = useLanguage()
  const loc = useCallback((val) => (typeof val === 'object' && val !== null) ? (val[language] || val.en || '') : (val || ''), [language])

  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Toolbar State
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('name_asc')
  const [filterType, setFilterType] = useState('all')
  const [filterDifficulty, setFilterDifficulty] = useState('all')
  const [viewMode, setViewMode] = useState('grid')
  const [showImport, setShowImport] = useState(false)
  const [activeTag, setActiveTag] = useState(null)

  useEffect(() => {
    fetch(`${getApiBase()}/api/admin/projects?stats=1`)
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

  const allTags = useMemo(() => {
    const tags = new Set()
    projects.forEach(p => (p.tags || []).forEach(tag => tags.add(tag)))
    return [...tags].sort()
  }, [projects])

  const processedProjects = useMemo(() => {
    let result = projects

    // 1. Filter
    if (search) {
      const q = search.toLowerCase()
      result = result.filter(p =>
        p.name?.toLowerCase().includes(q) ||
        loc(p.description)?.toLowerCase().includes(q) ||
        p.slug?.toLowerCase().includes(q) ||
        (p.tags || []).some(tag => tag.toLowerCase().includes(q))
      )
    }

    if (activeTag) {
      result = result.filter(p => (p.tags || []).includes(activeTag))
    }

    if (filterType !== 'all') {
      if (filterType === 'hyperobject') result = result.filter(p => p.is_hyperobject)
      if (filterType === 'demo') result = result.filter(p => p.is_demo)
    }

    if (filterDifficulty !== 'all') {
      result = result.filter(p => p.difficulty === filterDifficulty)
    }

    // 2. Sort
    result = [...result].sort((a, b) => {
      switch (sort) {
        case 'name_asc': return a.name.localeCompare(b.name)
        case 'name_desc': return b.name.localeCompare(a.name)
        case 'date_newest': return (b.modified_at || 0) - (a.modified_at || 0)
        case 'date_oldest': return (a.modified_at || 0) - (b.modified_at || 0)
        case 'complexity_asc': return (a.parameter_count || 0) - (b.parameter_count || 0)
        case 'complexity_desc': return (b.parameter_count || 0) - (a.parameter_count || 0)
        default: return 0
      }
    })

    return result
  }, [projects, search, activeTag, filterType, filterDifficulty, sort, loc])

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

  // Early return for empty projects (except when filtering)
  if (projects.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-muted-foreground">{t('projects.empty')}</p>
        <AuthGate tier="pro">
          <Button variant="outline" size="sm" onClick={() => setShowImport(true)} className="gap-1.5">
            {t('projects.empty_cta')}
          </Button>
        </AuthGate>
        {showImport && (
          <Suspense fallback={null}>
            <GitHubImportWizard
              onClose={() => setShowImport(false)}
              onImported={() => {
                setShowImport(false)
                // Refresh project list
                fetch(`${getApiBase()}/api/admin/projects`)
                  .then(res => res.ok ? res.json() : [])
                  .then(setProjects)
                  .catch(() => { })
              }}
            />
          </Suspense>
        )}
      </div>
    )
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold">{t('projects.title')}</h2>
          <AuthGate tier="pro">
            <Button variant="outline" size="sm" onClick={() => setShowImport(true)} className="gap-1.5">
              <Github className="h-4 w-4" />
              Import
            </Button>
          </AuthGate>
        </div>
      </div>

      {/* Toolbar */}
      <ProjectToolbar
        search={search}
        onSearchChange={setSearch}
        sort={sort}
        onSortChange={setSort}
        filterType={filterType}
        onFilterTypeChange={setFilterType}
        filterDifficulty={filterDifficulty}
        onFilterDifficultyChange={setFilterDifficulty}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        t={t}
      />

      {/* Tags (Legacy but useful) */}
      {allTags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {allTags.map(tag => (
            <button
              key={tag}
              type="button"
              className={`px-2.5 py-1 text-xs rounded-full border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${activeTag === tag
                ? 'bg-primary text-primary-foreground border-primary'
                : 'bg-background text-muted-foreground border-border hover:text-foreground'
                }`}
              onClick={() => setActiveTag(prev => prev === tag ? null : tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {processedProjects.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
          {t('projects.no_results')}
        </div>
      ) : (
        viewMode === 'list' ? (
          <ProjectList projects={processedProjects} loc={loc} t={t} />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {processedProjects.map(project => (
              <a
                key={project.slug}
                href={`#/${project.slug}`}
                className="block hover:ring-2 hover:ring-ring rounded-lg transition-shadow"
              >
                <Card className="h-full flex flex-col">
                  {project.thumbnail && (
                    <div className="aspect-video overflow-hidden rounded-t-lg bg-muted">
                      <img
                        src={project.thumbnail}
                        alt={project.name}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    </div>
                  )}
                  <CardHeader>
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-lg">{project.name}</CardTitle>
                      <span className="text-xs text-muted-foreground shrink-0">v{project.version}</span>
                    </div>
                    {project.description && (
                      <CardDescription className="line-clamp-2">{loc(project.description)}</CardDescription>
                    )}
                  </CardHeader>
                  <CardContent className="flex-1">
                    <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground px-0">
                      <span>{project.mode_count} mode{project.mode_count !== 1 ? 's' : ''}</span>
                      <span>·</span>
                      <span>{project.parameter_count} param{project.parameter_count !== 1 ? 's' : ''}</span>
                      {project.stats?.renders > 0 && (
                        <>
                          <span>·</span>
                          <span data-testid="stats-renders">{project.stats.renders} renders</span>
                        </>
                      )}
                      {project.stats?.exports > 0 && (
                        <>
                          <span>·</span>
                          <span data-testid="stats-exports">{project.stats.exports} exports</span>
                        </>
                      )}
                    </div>
                    {(project.tags || []).length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {project.tags.map(tag => (
                          <span key={tag} className="px-1.5 py-0.5 text-[10px] rounded bg-muted text-muted-foreground">{tag}</span>
                        ))}
                      </div>
                    )}
                  </CardContent>
                  <CardFooter className="gap-2 flex-wrap">
                    {project.difficulty && (
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${DIFFICULTY_COLORS[project.difficulty] || ''}`}>
                        {project.difficulty}
                      </span>
                    )}
                    {(() => {
                      const speed = getRenderSpeed(project.estimate_constants)
                      if (!speed) return null
                      return (
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${speed.color}`}>
                          {speed.label}
                        </span>
                      )
                    })()}
                    {project.has_manifest && <span data-testid="manifest-badge" className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold text-muted-foreground">{t('projects.manifest')}</span>}
                    {project.has_exports && <span data-testid="exports-badge" className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold text-muted-foreground">{t('projects.exports')}</span>}
                  </CardFooter>
                </Card>
              </a>
            ))}
          </div>
        )
      )}

      {showImport && (
        <Suspense fallback={null}>
          <GitHubImportWizard
            onClose={() => setShowImport(false)}
            onImported={() => {
              setShowImport(false)
              // Refresh project list
              fetch(`${getApiBase()}/api/admin/projects`)
                .then(res => res.ok ? res.json() : [])
                .then(setProjects)
                .catch(() => { })
            }}
          />
        </Suspense>
      )}
    </div>
  )
}
