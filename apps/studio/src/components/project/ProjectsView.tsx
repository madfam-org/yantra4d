import { useState, useEffect, useMemo, useCallback, useRef, lazy, Suspense } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  useVirtualizer,
  observeElementRect,
  measureElement as defaultMeasureElement,
  type Virtualizer,
  type Rect,
} from '@tanstack/react-virtual'
import { apiFetch } from '../../services/core/apiClient'
import { getApiBase } from '../../services/core/backendDetection'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Search, Github, SlidersHorizontal, X, LayoutGrid, GalleryHorizontal, Layers } from 'lucide-react'
import AuthGate from '../auth/AuthGate'
import fallbackManifest from '../../config/fallback-manifest.json'

const GitHubImportWizard = lazy(() => import('../ai/GitHubImportWizard'))
const ProjectCarousel3D = lazy(() => import('./ProjectCarousel3D'))
const StandardsBrowser = lazy(() => import('./StandardsBrowser'))

/** Max number of live-WebGL cards the 3D carousel can render before it degrades. */
const CAROUSEL_CAP = 24
/** Page size for the search API (server caps at 120). */
const PAGE_SIZE = 60
/** Facet sections whose (potentially long) value lists collapse behind a "show more". */
const LONG_FACET_SECTIONS = new Set(['standard', 'tag'])
const LONG_FACET_VISIBLE = 12
/** Debounce for the search box, in ms. */
const SEARCH_DEBOUNCE_MS = 250
/** Estimated row height (card + gap) used by the virtualizer before measurement. */
const ROW_ESTIMATE = 288
/**
 * Fallback viewport size when the scroll element reports 0×0 (before first
 * layout, or in test/JSDOM environments with no real layout engine). The
 * ResizeObserver corrects this once real dimensions are available.
 */
const FALLBACK_VIEWPORT: Rect = { width: 1200, height: 900 }

/**
 * Wrap the default rect observer so a 0-height measurement (pre-layout / JSDOM)
 * falls back to a usable viewport. Real layout always wins once observed.
 */
function observeElementRectWithFallback<
  TScroll extends Element,
  TItem extends Element,
>(instance: Virtualizer<TScroll, TItem>, cb: (rect: Rect) => void) {
  return observeElementRect(instance, (rect) => {
    cb({
      width: rect.width > 0 ? rect.width : FALLBACK_VIEWPORT.width,
      height: rect.height > 0 ? rect.height : FALLBACK_VIEWPORT.height,
    })
  })
}

/**
 * Row measurement that falls back to the estimate when the DOM reports a
 * 0-height row (pre-layout / JSDOM). Prevents the virtualizer from collapsing
 * every row to zero and rendering nothing.
 */
function measureRowWithFallback<TItem extends Element>(
  element: TItem,
  entry: ResizeObserverEntry | undefined,
  instance: Virtualizer<Element, TItem>,
): number {
  const measured = defaultMeasureElement(element, entry, instance)
  return measured > 0 ? measured : ROW_ESTIMATE
}

interface FacetValue {
  value: string
  count: number
}

interface CatalogFacets {
  domain: FacetValue[]
  difficulty: FacetValue[]
  engine: FacetValue[]
  geometry_type: FacetValue[]
  standard: FacetValue[]
  material: FacetValue[]
  tag: FacetValue[]
}

interface CatalogResult {
  slug: string
  name: string
  name_i18n?: { en?: string; es?: string } | null
  description?: string
  engine?: string
  difficulty?: string
  domain?: string
  is_hyperobject?: boolean
  dual_engine?: boolean
  tags?: string[]
  geometry_types?: string[]
  standards?: string[]
  material_aware?: boolean
  material_capabilities?: string[]
  mode_count?: number
  part_count?: number
  thumbnail?: string
  modified_ms?: number
  unlisted?: boolean
}

interface SearchResponse {
  results: CatalogResult[]
  total: number
  limit: number
  offset: number
  facets: CatalogFacets
  catalog_count: number
}

/** The facet dimensions we render as filter sections, in display order. */
type FacetKey = 'domain' | 'geometry_type' | 'standard' | 'material' | 'difficulty' | 'engine'

const FACET_ORDER: FacetKey[] = ['domain', 'geometry_type', 'standard', 'material', 'difficulty', 'engine']

/**
 * Material-awareness facet values are raw capability-flag names from the API
 * (stable, used verbatim as the `material` query param). Map each to a localized
 * chip label; unknown / non-material facet values fall through to the raw value.
 */
const MATERIAL_CAPABILITY_I18N: Record<string, string> = {
  tolerance_by_material: 'projects.filter.material.tolerance_by_material',
  shrinkage_compensation: 'projects.filter.material.shrinkage_compensation',
  recycled_material_toggle: 'projects.filter.material.recycled_material_toggle',
}

/** API sort values keyed by the select control value. */
const SORT_OPTIONS = ['name', 'recent', 'complexity'] as const
type SortOption = (typeof SORT_OPTIONS)[number]

const DIFFICULTY_COLORS: Record<string, string> = {
  beginner: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  intermediate: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  advanced: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
}

const EMPTY_FACETS: CatalogFacets = {
  domain: [],
  difficulty: [],
  engine: [],
  geometry_type: [],
  standard: [],
  material: [],
  tag: [],
}

/** Deterministic neutral gradient tile for missing/broken thumbnails. */
function placeholderGradient(seed: string): string {
  let hash = 0
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) & 0xffff
  const hue = hash % 360
  return `linear-gradient(135deg, hsl(${hue} 45% 82%), hsl(${(hue + 40) % 360} 45% 68%))`
}

/** Number of grid columns for a given container width (mobile-first: 1→4). */
function columnsForWidth(width: number): number {
  if (width >= 1100) return 4
  if (width >= 800) return 3
  if (width >= 520) return 2
  return 1
}

interface FacetSectionProps {
  facetKey: FacetKey
  title: string
  values: FacetValue[]
  active: string[]
  onToggle: (facet: FacetKey, value: string) => void
}

function FacetSection({ facetKey, title, values, active, onToggle }: FacetSectionProps) {
  const [expanded, setExpanded] = useState(false)
  const { t } = useLanguage()

  // Post-filter counts already exclude zero-count values, but guard anyway so we
  // never render a chip that yields no results.
  const visibleValues = values.filter((v) => v.count > 0 || active.includes(v.value))
  if (visibleValues.length === 0) return null

  const collapsible = LONG_FACET_SECTIONS.has(facetKey) && visibleValues.length > LONG_FACET_VISIBLE
  const shown = collapsible && !expanded ? visibleValues.slice(0, LONG_FACET_VISIBLE) : visibleValues

  return (
    <div className="border-b border-border pb-4 last:border-b-0">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h3>
      <ul className="flex flex-wrap gap-1.5">
        {shown.map((fv) => {
          const isActive = active.includes(fv.value)
          // Material facet values are raw capability flags → show a localized label;
          // every other facet renders its value verbatim.
          const labelKey = facetKey === 'material' ? MATERIAL_CAPABILITY_I18N[fv.value] : undefined
          const label = labelKey ? t(labelKey) : fv.value
          return (
            <li key={fv.value}>
              <button
                type="button"
                aria-pressed={isActive}
                onClick={() => onToggle(facetKey, fv.value)}
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                  isActive
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border bg-background text-foreground hover:bg-accent hover:text-accent-foreground'
                }`}
              >
                <span>{label}</span>
                <span
                  className={`tabular-nums ${isActive ? 'text-primary-foreground/80' : 'text-muted-foreground'}`}
                >
                  {fv.count}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
      {collapsible && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 text-xs font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
        >
          {expanded ? t('projects.filter.show_less') : t('projects.filter.show_more')}
        </button>
      )}
    </div>
  )
}

interface FilterSidebarProps {
  facets: CatalogFacets
  facetTitles: Record<FacetKey, string>
  active: Record<FacetKey, string[]>
  onToggle: (facet: FacetKey, value: string) => void
}

function FilterSidebar({ facets, facetTitles, active, onToggle }: FilterSidebarProps) {
  return (
    <div className="flex flex-col gap-4">
      {FACET_ORDER.map((key) => (
        <FacetSection
          key={key}
          facetKey={key}
          title={facetTitles[key]}
          values={facets[key] ?? []}
          active={active[key]}
          onToggle={onToggle}
        />
      ))}
    </div>
  )
}

interface ProjectCardProps {
  project: CatalogResult
  displayName: string
  description: string
  t: (key: string, params?: Record<string, string | number>) => string
}

function ProjectCard({ project, displayName, description, t }: ProjectCardProps) {
  const [thumbFailed, setThumbFailed] = useState(false)
  const initial = (displayName || project.slug || '?').charAt(0).toUpperCase()
  const showImage = project.thumbnail && !thumbFailed
  const geometry = (project.geometry_types ?? []).slice(0, 2)
  const standards = (project.standards ?? []).slice(0, 1)

  return (
    <Link
      to={`/project/${project.slug}`}
      className="group block h-full rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Card className="flex h-full flex-col overflow-hidden transition-transform duration-150 group-hover:-translate-y-0.5 group-hover:shadow-md">
        <div className="relative aspect-video overflow-hidden bg-muted">
          {showImage ? (
            <img
              src={project.thumbnail}
              alt={displayName}
              loading="lazy"
              className="h-full w-full object-cover"
              onError={() => setThumbFailed(true)}
            />
          ) : (
            <div
              aria-hidden="true"
              className="flex h-full w-full items-center justify-center text-3xl font-bold text-white/90"
              style={{ backgroundImage: placeholderGradient(project.slug) }}
            >
              {initial}
            </div>
          )}
          {project.difficulty && (
            <span
              className={`absolute right-2 top-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                DIFFICULTY_COLORS[project.difficulty] || 'bg-muted text-foreground'
              }`}
            >
              {t(`projects.filter.difficulty.${project.difficulty}`) || project.difficulty}
            </span>
          )}
        </div>
        <div className="flex flex-1 flex-col gap-1.5 p-4">
          <h3 className="text-base font-semibold leading-tight">{displayName}</h3>
          {description && (
            <p className="line-clamp-1 text-sm text-muted-foreground">{description}</p>
          )}
          {(geometry.length > 0 || standards.length > 0) && (
            <div className="mt-auto flex flex-wrap gap-1 pt-2">
              {geometry.map((g) => (
                <span
                  key={`g-${g}`}
                  className="inline-flex items-center rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground"
                >
                  {g}
                </span>
              ))}
              {standards.map((s) => (
                <span
                  key={`s-${s}`}
                  className="inline-flex items-center rounded border border-primary/40 bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-foreground"
                >
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      </Card>
    </Link>
  )
}

function CardSkeleton() {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-border bg-card">
      <div className="aspect-video bg-muted" />
      <div className="flex flex-col gap-2 p-4">
        <div className="h-4 w-3/4 rounded bg-muted" />
        <div className="h-3 w-full rounded bg-muted" />
        <div className="h-3 w-1/3 rounded bg-muted" />
      </div>
    </div>
  )
}

const EMPTY_ACTIVE: Record<FacetKey, string[]> = {
  domain: [],
  geometry_type: [],
  standard: [],
  material: [],
  difficulty: [],
  engine: [],
}

export default function ProjectsView() {
  const { t, language } = useLanguage()
  const navigate = useNavigate()

  const [results, setResults] = useState<CatalogResult[]>([])
  const [facets, setFacets] = useState<CatalogFacets>(EMPTY_FACETS)
  const [total, setTotal] = useState(0)
  const [catalogCount, setCatalogCount] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [searchInput, setSearchInput] = useState('')
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<SortOption>('name')
  const [active, setActive] = useState<Record<FacetKey, string[]>>(EMPTY_ACTIVE)
  const [viewMode, setViewMode] = useState<'grid' | 'carousel3D'>('grid')
  const [browseByStandard, setBrowseByStandard] = useState(false)
  const [filterSheetOpen, setFilterSheetOpen] = useState(false)
  const [showImport, setShowImport] = useState(false)

  const gridScrollRef = useRef<HTMLDivElement>(null)
  const [columns, setColumns] = useState(1)

  // Debounce the search box → drives the API `q` param.
  useEffect(() => {
    const handle = setTimeout(() => setQuery(searchInput.trim()), SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(handle)
  }, [searchInput])

  const buildUrl = useCallback(
    (pageOffset: number) => {
      const params = new URLSearchParams()
      if (query) params.set('q', query)
      for (const [key, values] of Object.entries(active)) {
        for (const value of values) {
          // geometry_type + difficulty + engine + domain + standard all map 1:1;
          // the API expects `geometry_type`, `standard`, `domain`, `difficulty`, `engine`.
          params.append(key, value)
        }
      }
      params.set('sort', sort)
      params.set('limit', String(PAGE_SIZE))
      params.set('offset', String(pageOffset))
      return `${getApiBase()}/api/catalog/search?${params.toString()}`
    },
    [query, active, sort],
  )

  // Primary fetch: whenever the query, filters, or sort change we reset to offset 0.
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setOffset(0)
    apiFetch(buildUrl(0))
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: SearchResponse) => {
        if (cancelled) return
        setResults(data.results || [])
        setFacets(data.facets || EMPTY_FACETS)
        setTotal(data.total || 0)
        setCatalogCount(data.catalog_count || 0)
        setLoading(false)
      })
      .catch((err: Error) => {
        if (cancelled) return
        setError(err.message)
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [buildUrl])

  const loadMore = useCallback(() => {
    if (loadingMore || loading) return
    if (results.length >= total) return
    const nextOffset = offset + PAGE_SIZE
    setLoadingMore(true)
    apiFetch(buildUrl(nextOffset))
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: SearchResponse) => {
        setResults((prev) => [...prev, ...(data.results || [])])
        setOffset(nextOffset)
        setLoadingMore(false)
      })
      .catch(() => {
        // Non-fatal: keep what we have, allow the user to retry via the button.
        setLoadingMore(false)
      })
  }, [buildUrl, loadingMore, loading, results.length, total, offset])

  const retry = useCallback(() => {
    // Re-run the primary effect by nudging state it depends on.
    setError(null)
    setLoading(true)
    apiFetch(buildUrl(0))
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: SearchResponse) => {
        setResults(data.results || [])
        setFacets(data.facets || EMPTY_FACETS)
        setTotal(data.total || 0)
        setCatalogCount(data.catalog_count || 0)
        setLoading(false)
      })
      .catch((err: Error) => {
        setError(err.message)
        setLoading(false)
      })
  }, [buildUrl])

  const toggleFacet = useCallback((facet: FacetKey, value: string) => {
    setActive((prev) => {
      const current = prev[facet]
      const next = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value]
      return { ...prev, [facet]: next }
    })
  }, [])

  const clearFacet = useCallback((facet: FacetKey, value: string) => {
    setActive((prev) => ({ ...prev, [facet]: prev[facet].filter((v) => v !== value) }))
  }, [])

  const clearAll = useCallback(() => {
    setActive(EMPTY_ACTIVE)
    setSearchInput('')
    setQuery('')
  }, [])

  const activePills = useMemo(() => {
    const pills: { facet: FacetKey; value: string }[] = []
    for (const key of FACET_ORDER) {
      for (const value of active[key]) pills.push({ facet: key, value })
    }
    return pills
  }, [active])

  const hasActiveFilters = activePills.length > 0 || query.length > 0

  const facetTitles = useMemo<Record<FacetKey, string>>(
    () => ({
      domain: t('projects.filter.domain'),
      geometry_type: t('projects.filter.connects_via'),
      standard: t('projects.filter.compatible_with'),
      material: t('projects.filter.material'),
      difficulty: t('projects.filter.difficulty.title'),
      engine: t('projects.filter.engine'),
    }),
    [t],
  )

  // Localize a facet value for display (active-filter pills). Only the material
  // facet carries coded values; everything else is already human-readable.
  const facetValueLabel = useCallback(
    (facet: FacetKey, value: string) => {
      const key = facet === 'material' ? MATERIAL_CAPABILITY_I18N[value] : undefined
      return key ? t(key) : value
    },
    [t],
  )

  const displayName = useCallback(
    (p: CatalogResult) => p.name_i18n?.[language as 'en' | 'es'] || p.name_i18n?.en || p.name || '',
    [language],
  )

  const cappedCarouselProjects = useMemo(() => results.slice(0, CAROUSEL_CAP), [results])

  // Track container width so the grid picks a mobile-first column count.
  useEffect(() => {
    const el = gridScrollRef.current
    if (!el) return
    const measure = () => {
      const width = el.clientWidth || el.getBoundingClientRect().width
      if (width > 0) setColumns(columnsForWidth(width))
    }
    measure()
    if (typeof ResizeObserver !== 'undefined') {
      const ro = new ResizeObserver(measure)
      ro.observe(el)
      return () => ro.disconnect()
    }
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [loading])

  const rowCount = Math.ceil(results.length / columns)

  const rowVirtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => gridScrollRef.current,
    estimateSize: () => ROW_ESTIMATE,
    overscan: 4,
    // Give the virtualizer a viewport even when the scroll element reports a
    // zero-height rect (pre-layout / JSDOM), so results render immediately.
    initialRect: FALLBACK_VIEWPORT,
    observeElementRect: observeElementRectWithFallback,
    measureElement: measureRowWithFallback,
  })

  const virtualRows = rowVirtualizer.getVirtualItems()

  const importWizard = showImport ? (
    <Suspense fallback={null}>
      <GitHubImportWizard
        onClose={() => setShowImport(false)}
        onImported={() => {
          setShowImport(false)
          retry()
        }}
      />
    </Suspense>
  ) : null

  // --- Loading (initial) ---
  if (loading) {
    return (
      <div className="mx-auto max-w-7xl p-6">
        <div className="mb-6 h-8 w-40 rounded bg-muted" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <span className="sr-only">{t('projects.loading')}</span>
      </div>
    )
  }

  // --- Error ---
  if (error) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <p className="text-destructive">
          {t('projects.error')}
          {error}
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={retry}>
            {t('status.retry')}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() =>
              navigate(
                `/project/${(fallbackManifest as Record<string, unknown> & { project: { slug: string } }).project.slug}`,
              )
            }
          >
            {t('projects.open_demo')}
          </Button>
        </div>
      </div>
    )
  }

  const resultCountLabel = query
    ? t('projects.results_for', { count: total, query })
    : t('projects.results_count', { count: total })

  const sidebar = (
    <FilterSidebar
      facets={facets}
      facetTitles={facetTitles}
      active={active}
      onToggle={toggleFacet}
    />
  )

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      {/* Header */}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold">{t('projects.title')}</h2>
          <span className="text-sm text-muted-foreground">
            {t('projects.catalog_size', { count: catalogCount })}
          </span>
        </div>
        <AuthGate tier="pro">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowImport(true)}
            className="gap-1.5 min-h-[44px] md:min-h-0"
          >
            <Github className="h-4 w-4" />
            {t('projects.import')}
          </Button>
        </AuthGate>
      </div>

      {/* Controls row */}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative w-full sm:max-w-sm">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <label htmlFor="projects-search" className="sr-only">
            {t('projects.search')}
          </label>
          <input
            id="projects-search"
            type="search"
            placeholder={t('projects.search')}
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="min-h-[44px] w-full rounded-md border border-border bg-background py-2 pl-9 pr-3 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:min-h-0 md:text-sm"
          />
        </div>

        <div className="flex items-center gap-2">
          {/* Mobile filter trigger */}
          <Sheet open={filterSheetOpen} onOpenChange={setFilterSheetOpen}>
            <SheetTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 min-h-[44px] md:min-h-0 lg:hidden"
              >
                <SlidersHorizontal className="h-4 w-4" />
                {t('projects.filter.title')}
                {activePills.length > 0 && (
                  <span className="ml-0.5 rounded-full bg-primary px-1.5 text-xs text-primary-foreground tabular-nums">
                    {activePills.length}
                  </span>
                )}
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-80 overflow-y-auto">
              <SheetHeader>
                <SheetTitle>{t('projects.filter.title')}</SheetTitle>
              </SheetHeader>
              <div className="mt-4">{sidebar}</div>
            </SheetContent>
          </Sheet>

          <Select value={sort} onValueChange={(v) => setSort(v as SortOption)}>
            <SelectTrigger className="h-11 w-[150px] min-h-[44px] md:h-9 md:min-h-0" aria-label={t('projects.sort.label')}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="name">{t('projects.sort.name')}</SelectItem>
              <SelectItem value="recent">{t('projects.sort.recent')}</SelectItem>
              <SelectItem value="complexity">{t('projects.sort.complexity')}</SelectItem>
            </SelectContent>
          </Select>

          <ToggleGroup
            type="single"
            value={viewMode}
            onValueChange={(v) => v && setViewMode(v as 'grid' | 'carousel3D')}
          >
            <ToggleGroupItem
              value="grid"
              aria-label={t('projects.view.grid')}
              className="h-11 w-11 min-h-[44px] min-w-[44px] p-0 md:h-9 md:w-9 md:min-h-0 md:min-w-0"
            >
              <LayoutGrid className="h-4 w-4" />
            </ToggleGroupItem>
            <ToggleGroupItem
              value="carousel3D"
              aria-label={t('projects.view.carousel3d')}
              className="h-11 w-11 min-h-[44px] min-w-[44px] p-0 md:h-9 md:w-9 md:min-h-0 md:min-w-0"
            >
              <GalleryHorizontal className="h-4 w-4" />
            </ToggleGroupItem>
          </ToggleGroup>

          <Button
            variant={browseByStandard ? 'default' : 'outline'}
            size="sm"
            aria-pressed={browseByStandard}
            onClick={() => setBrowseByStandard((v) => !v)}
            className="gap-1.5 min-h-[44px] md:min-h-0"
          >
            <Layers className="h-4 w-4" />
            {t('standards.title')}
          </Button>
        </div>
      </div>

      {browseByStandard ? (
        <Suspense
          fallback={
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              {t('standards.loading')}
            </div>
          }
        >
          <StandardsBrowser />
        </Suspense>
      ) : (
        <>
      {/* Result count + active filter pills */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <p aria-live="polite" className="text-sm font-medium text-foreground">
          {resultCountLabel}
        </p>
        {hasActiveFilters && (
          <>
            <span className="text-muted-foreground" aria-hidden="true">
              ·
            </span>
            {activePills.map((pill) => {
              const pillLabel = facetValueLabel(pill.facet, pill.value)
              return (
                <button
                  key={`${pill.facet}-${pill.value}`}
                  type="button"
                  onClick={() => clearFacet(pill.facet, pill.value)}
                  className="inline-flex items-center gap-1 rounded-full border border-primary bg-primary/10 px-2 py-0.5 text-xs text-foreground hover:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {pillLabel}
                  <X className="h-3 w-3" aria-hidden="true" />
                  <span className="sr-only">{t('projects.filter.remove', { value: pillLabel })}</span>
                </button>
              )
            })}
            <button
              type="button"
              onClick={clearAll}
              className="text-xs font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            >
              {t('projects.filter.clear_all')}
            </button>
          </>
        )}
      </div>

      <div className="flex gap-6">
        {/* Desktop sidebar */}
        <aside className="hidden w-64 shrink-0 lg:block" aria-label={t('projects.filter.title')}>
          {sidebar}
        </aside>

        {/* Results */}
        <div className="min-w-0 flex-1">
          {viewMode === 'carousel3D' ? (
            results.length === 0 ? (
              <div className="flex h-32 items-center justify-center text-muted-foreground">
                {hasActiveFilters ? t('projects.no_results') : t('projects.empty')}
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {results.length > CAROUSEL_CAP && (
                  <p className="text-xs text-muted-foreground">
                    {t('projects.carousel_capped', { count: CAROUSEL_CAP })}
                  </p>
                )}
                <Suspense
                  fallback={
                    <div className="flex h-96 items-center justify-center text-muted-foreground">
                      {t('projects.loading')}
                    </div>
                  }
                >
                  <ProjectCarousel3D projects={cappedCarouselProjects} />
                </Suspense>
              </div>
            )
          ) : results.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
              <p className="text-muted-foreground">
                {hasActiveFilters ? t('projects.no_results') : t('projects.empty')}
              </p>
              {hasActiveFilters ? (
                <Button variant="outline" size="sm" onClick={clearAll}>
                  {t('projects.filter.clear_all')}
                </Button>
              ) : (
                <AuthGate tier="pro">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowImport(true)}
                    className="min-h-[44px] md:min-h-0"
                  >
                    {t('projects.empty_cta')}
                  </Button>
                </AuthGate>
              )}
            </div>
          ) : (
            <>
              <div
                ref={gridScrollRef}
                className="max-h-[calc(100dvh-16rem)] overflow-y-auto pr-1"
                data-testid="projects-grid-scroll"
                onScroll={(e) => {
                  const el = e.currentTarget
                  if (el.scrollHeight - el.scrollTop - el.clientHeight < 400) loadMore()
                }}
              >
                <div className="relative w-full" style={{ height: `${rowVirtualizer.getTotalSize()}px` }}>
                  {virtualRows.map((virtualRow) => {
                    const startIndex = virtualRow.index * columns
                    const rowItems = results.slice(startIndex, startIndex + columns)
                    return (
                      <div
                        key={virtualRow.key}
                        data-index={virtualRow.index}
                        ref={rowVirtualizer.measureElement}
                        className="absolute left-0 top-0 w-full"
                        style={{ transform: `translateY(${virtualRow.start}px)` }}
                      >
                        <div
                          className="grid gap-4 pb-4"
                          style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
                        >
                          {rowItems.map((project) => (
                            <ProjectCard
                              key={project.slug}
                              project={project}
                              displayName={displayName(project)}
                              description={project.description || ''}
                              t={t}
                            />
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {results.length < total && (
                <div className="mt-4 flex justify-center">
                  <Button variant="outline" size="sm" onClick={loadMore} disabled={loadingMore}>
                    {loadingMore ? t('projects.loading') : t('projects.load_more')}
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
        </>
      )}

      {importWizard}
    </div>
  )
}
