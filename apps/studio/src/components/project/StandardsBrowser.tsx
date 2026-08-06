import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../services/core/apiClient'
import { getApiBase } from '../../services/core/backendDetection'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Layers, ChevronRight, ChevronDown } from 'lucide-react'

/** One standard-family cluster from GET /api/catalog/families. */
interface StandardFamily {
  /** Canonical family key, e.g. "vesa", "unc-1/4-20", "din-rail-35". */
  family: string
  /** Number of catalog objects that expose an interface in this family. */
  members: number
  /** Slugs of the member objects, for building member cards. */
  slugs: string[]
}

interface FamiliesResponse {
  families: StandardFamily[]
  count: number
}

interface StandardsBrowserProps {
  /**
   * Optional override for the families data (used by tests / storybook).
   * When omitted the component fetches GET /api/catalog/families itself.
   */
  families?: StandardFamily[]
}

type LoadState = 'loading' | 'loaded' | 'error'

/**
 * Human-friendly labels for the internal family keys produced by
 * `normalize_family` (services/core/compatibility_graph.py). Keys not listed
 * here fall back to a title-cased version of the raw key (`familyLabel`), so a
 * newly-added family is always readable even before it gets a curated label.
 */
const FAMILY_LABELS: Record<string, string> = {
  'unc-1/4-20': '1/4-20 UNC',
  'unc-3/8-16': '3/8-16 UNC',
  vesa: 'VESA',
  'nema-stepper': 'NEMA stepper',
  gridfinity: 'Gridfinity',
  multiboard: 'Multiboard',
  'din-rail-35': 'DIN rail (35mm)',
  'pco-1881': 'PCO 1881',
  'ght-hose': 'GHT (garden hose)',
  npt: 'NPT',
  bsp: 'BSP',
  'arca-swiss': 'Arca-Swiss',
  picatinny: 'Picatinny',
  'nato-rail': 'NATO rail',
  'gopro-mount': 'GoPro mount',
  'iso-518-shoe': 'ISO 518 shoe',
  '15mm-rod': '15mm rod (LWS)',
  mc4: 'MC4',
  'e26-e27-lamp': 'E26 / E27 lamp',
  'gu10-lamp': 'GU10 lamp',
  'b22-lamp': 'B22 lamp',
  'aerator-m22-m24': 'Aerator (M22 / M24)',
  'cable-gland': 'Cable gland',
  'timing-belt': 'Timing belt',
  't-slot-extrusion': 'T-slot extrusion',
  'miter-ttrack': 'Miter / T-track',
  'addressable-led': 'Addressable LED',
  'led-matrix': 'LED matrix',
  'rms-objective': 'RMS objective',
  'optical-breadboard': 'Optical breadboard',
  'molle-pals': 'MOLLE / PALS',
  'iso-m3': 'ISO M3',
  'iso-m4': 'ISO M4',
  'iso-m5': 'ISO M5',
  'iso-m6': 'ISO M6',
  'iso-m8': 'ISO M8',
  'bearing-608': 'Bearing (608)',
  'involute-gear': 'Involute gear',
  'worm-gear': 'Worm gear',
  'bevel-gear': 'Bevel gear',
  'webbing-strap': 'Webbing strap',
  'pc-fan': 'PC fan',
  'battery-cell': 'Battery cell',
  'filter-thread': 'Filter thread',
  'drip-irrigation': 'Drip irrigation',
  conduit: 'Conduit (EMT)',
  'net-cup': 'Net cup',
  'iso-hex-fastener': 'ISO hex fastener',
  'shaft-spline': 'Shaft / spline',
  'servo-spline': 'Servo spline',
  multiconnect: 'Multiconnect',
  'psu-mount': 'PSU mount',
  'cam-lock': 'Cam lock',
  'enable-prosthetic': 'e-NABLE prosthetic',
  'wall-stud': 'Wall stud',
  'usb-sd-media': 'USB / SD media',
  'round-rail-25': 'Round rail (25mm)',
  'beverage-can': 'Beverage can',
  cuvette: 'Cuvette',
  'compass-capsule': 'Compass capsule',
  'card-format': 'Card format',
}

/** Title-case a raw family key as a readable fallback ("foo-bar" → "Foo Bar"). */
function titleCaseKey(key: string): string {
  return key
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((word) => (word ? word.charAt(0).toUpperCase() + word.slice(1) : word))
    .join(' ')
}

/** Curated label for a family key, falling back to a title-cased key. */
export function familyLabel(key: string): string {
  return FAMILY_LABELS[key] ?? titleCaseKey(key)
}

/** Turn a slug ("nema-17-mount") into a readable display name ("Nema 17 Mount"). */
function slugToName(slug: string): string {
  return titleCaseKey(slug)
}

/**
 * Deterministic neutral gradient tile for missing/broken thumbnails.
 * Mirrors the fallback used by ProjectsView / WorksWithPanel so member tiles
 * feel native across the catalog surfaces.
 */
function placeholderGradient(seed: string): string {
  let hash = 0
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) & 0xffff
  const hue = hash % 360
  return `linear-gradient(135deg, hsl(${hue} 45% 82%), hsl(${(hue + 40) % 360} 45% 68%))`
}

interface MemberCardProps {
  slug: string
}

/**
 * A single member object of a standard family. Links to /project/<slug> and
 * shows the generated placeholder thumbnail (/projects/<slug>.svg) with a
 * gradient fallback — the same thumbnail + onError pattern as WorksWithPanel.
 */
function MemberCard({ slug }: MemberCardProps) {
  const [thumbFailed, setThumbFailed] = useState(false)
  const name = slugToName(slug)
  const initial = (name || slug || '?').charAt(0).toUpperCase()
  const thumbnail = `/projects/${slug}.svg`
  const showImage = !thumbFailed

  return (
    <Link
      to={`/project/${slug}`}
      className="group block h-full rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Card className="flex h-full items-center gap-3 overflow-hidden p-2 transition-colors group-hover:bg-accent group-hover:text-accent-foreground">
        <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded bg-muted">
          {showImage ? (
            <img
              src={thumbnail}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover"
              onError={() => setThumbFailed(true)}
            />
          ) : (
            <span
              aria-hidden="true"
              className="flex h-full w-full items-center justify-center text-base font-bold text-white/90"
              style={{ backgroundImage: placeholderGradient(slug) }}
            >
              {initial}
            </span>
          )}
        </div>
        <span className="min-w-0 flex-1 truncate text-sm font-medium leading-tight">{name}</span>
      </Card>
    </Link>
  )
}

interface FamilyRowProps {
  family: StandardFamily
  expanded: boolean
  onToggle: (family: string) => void
  t: (key: string, params?: Record<string, string | number>) => string
}

/**
 * One family in the directory: a clickable header (label + member count) that
 * expands to reveal its member objects inline as cards.
 */
function FamilyRow({ family, expanded, onToggle, t }: FamilyRowProps) {
  const label = familyLabel(family.family)
  const panelId = `standards-family-${family.family.replace(/[^a-z0-9]+/gi, '-')}`

  return (
    <li className="overflow-hidden rounded-lg border border-border bg-card">
      <button
        type="button"
        aria-expanded={expanded}
        aria-controls={panelId}
        onClick={() => onToggle(family.family)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        )}
        <span className="min-w-0 flex-1 truncate text-sm font-semibold">{label}</span>
        <span className="shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium tabular-nums text-foreground">
          {t('standards.members', { count: family.members })}
        </span>
      </button>

      {expanded && (
        <div id={panelId} className="border-t border-border p-3">
          {family.slugs.length === 0 ? (
            <p className="px-1 py-2 text-xs text-muted-foreground">{t('standards.no_members')}</p>
          ) : (
            <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {family.slugs.map((slug) => (
                <li key={slug}>
                  <MemberCard slug={slug} />
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </li>
  )
}

function DirectorySkeleton() {
  return (
    <ul className="flex flex-col gap-2" aria-hidden="true">
      {Array.from({ length: 6 }).map((_, i) => (
        <li key={i} className="flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-3">
          <div className="h-4 w-4 shrink-0 rounded bg-muted" />
          <div className="h-4 flex-1 rounded bg-muted" />
          <div className="h-4 w-10 shrink-0 rounded-full bg-muted" />
        </li>
      ))}
    </ul>
  )
}

/**
 * "Browse by standard" — a directory of the real-world interoperability
 * families the catalog speaks (NEMA, VESA, Gridfinity, 1/4-20, DIN-rail, GHT…),
 * each ranked by member count. Clicking a family expands its member objects
 * inline as cards linking to /project/<slug>.
 *
 * Consumes GET /api/catalog/families. Never throws into its parent: loading /
 * error / empty states are all rendered inline (same contract as WorksWithPanel).
 */
export default function StandardsBrowser({ families: familiesProp }: StandardsBrowserProps) {
  const { t } = useLanguage()
  const controlled = familiesProp !== undefined
  const [state, setState] = useState<LoadState>(controlled ? 'loaded' : 'loading')
  const [families, setFamilies] = useState<StandardFamily[]>(familiesProp ?? [])
  const [expanded, setExpanded] = useState<string | null>(null)
  // Bumped by retry to force the fetch effect to re-run.
  const [reloadNonce, setReloadNonce] = useState(0)

  // Fetch the family directory once (unless data was supplied via props). This
  // synchronizes React with the external catalog API; the leading reset to
  // 'loading' mirrors the intentional pattern used by ProjectsView /
  // WorksWithPanel so the skeleton shows immediately on retry.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (controlled) return
    let cancelled = false
    setState('loading')
    apiFetch(`${getApiBase()}/api/catalog/families`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: FamiliesResponse) => {
        if (cancelled) return
        setFamilies(Array.isArray(data.families) ? data.families : [])
        setState('loaded')
      })
      .catch(() => {
        if (cancelled) return
        setState('error')
      })
    return () => {
      cancelled = true
    }
  }, [controlled, reloadNonce])
  /* eslint-enable react-hooks/set-state-in-effect */

  const retry = useCallback(() => setReloadNonce((n) => n + 1), [])

  const toggle = useCallback((family: string) => {
    setExpanded((prev) => (prev === family ? null : family))
  }, [])

  const total = useMemo(() => families.length, [families])

  return (
    <section aria-labelledby="standards-heading" className="space-y-3">
      <div>
        <h3
          id="standards-heading"
          className="flex items-center gap-1.5 text-base font-semibold leading-tight"
        >
          <Layers className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          {t('standards.title')}
        </h3>
        {state === 'loaded' && total > 0 && (
          <p className="mt-0.5 text-sm text-muted-foreground">
            {t('standards.subtitle', { count: total })}
          </p>
        )}
      </div>

      {state === 'loading' && (
        <div aria-busy="true">
          <span className="sr-only">{t('standards.loading')}</span>
          <DirectorySkeleton />
        </div>
      )}

      {state === 'error' && (
        <div className="flex flex-col items-start gap-2 rounded-md border border-border bg-muted/40 p-4">
          <p className="text-sm text-muted-foreground">{t('standards.error')}</p>
          <Button variant="outline" size="sm" onClick={retry}>
            {t('standards.retry')}
          </Button>
        </div>
      )}

      {state === 'loaded' && total === 0 && (
        <p className="rounded-md border border-dashed border-border bg-muted/30 p-4 text-sm leading-relaxed text-muted-foreground">
          {t('standards.empty')}
        </p>
      )}

      {state === 'loaded' && total > 0 && (
        <ul className="flex flex-col gap-2">
          {families.map((family) => (
            <FamilyRow
              key={family.family}
              family={family}
              expanded={expanded === family.family}
              onToggle={toggle}
              t={t}
            />
          ))}
        </ul>
      )}
    </section>
  )
}
