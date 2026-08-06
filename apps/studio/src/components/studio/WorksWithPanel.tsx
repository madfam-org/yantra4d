import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../services/core/apiClient'
import { getApiBase } from '../../services/core/backendDetection'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Link2, Layers } from 'lucide-react'

/** A single shared-standard reason connecting two objects. */
interface WorksWithReason {
  family: string
  kind: 'mates_with' | 'same_family'
  via: string
  geometry: string
}

/** A partner object that physically interfaces with the current one. */
interface WorksWithPartner {
  slug: string
  name: string
  domain: string
  thumbnail: string
  reasons: WorksWithReason[]
}

interface WorksWithResponse {
  slug: string
  count: number
  partners: WorksWithPartner[]
}

interface WorksWithPanelProps {
  /** Slug of the currently-open hyperobject. */
  slug: string
}

type LoadState = 'loading' | 'loaded' | 'error'

/**
 * Deterministic neutral gradient tile for missing/broken thumbnails.
 * Mirrors the fallback used by ProjectsView so companion tiles feel native.
 */
function placeholderGradient(seed: string): string {
  let hash = 0
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) & 0xffff
  const hue = hash % 360
  return `linear-gradient(135deg, hsl(${hue} 45% 82%), hsl(${(hue + 40) % 360} 45% 68%))`
}

interface PartnerRowProps {
  partner: WorksWithPartner
  t: (key: string, params?: Record<string, string | number>) => string
}

function PartnerRow({ partner, t }: PartnerRowProps) {
  const [thumbFailed, setThumbFailed] = useState(false)
  const primary = partner.reasons[0]
  const extraReasons = partner.reasons.length - 1
  const initial = (partner.name || partner.slug || '?').charAt(0).toUpperCase()
  const showImage = partner.thumbnail && !thumbFailed
  const mates = primary?.kind === 'mates_with'

  return (
    <li>
      <Link
        to={`/project/${partner.slug}`}
        aria-label={t('works_with.view_partner', { name: partner.name })}
        className="group flex items-center gap-3 rounded-md border border-border bg-card p-2 transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <div className="relative h-10 w-10 shrink-0 overflow-hidden rounded bg-muted">
          {showImage ? (
            <img
              src={partner.thumbnail}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover"
              onError={() => setThumbFailed(true)}
            />
          ) : (
            <span
              aria-hidden="true"
              className="flex h-full w-full items-center justify-center text-sm font-bold text-white/90"
              style={{ backgroundImage: placeholderGradient(partner.slug) }}
            >
              {initial}
            </span>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="truncate text-sm font-medium leading-tight">{partner.name}</span>
            <span
              className={`inline-flex shrink-0 items-center gap-0.5 text-[10px] font-medium ${
                mates ? 'text-primary' : 'text-muted-foreground'
              }`}
            >
              {mates ? (
                <Link2 className="h-3 w-3" aria-hidden="true" />
              ) : (
                <Layers className="h-3 w-3" aria-hidden="true" />
              )}
              {mates ? t('works_with.mates') : t('works_with.same_family')}
            </span>
          </div>
          {primary && (
            <div className="mt-1 flex flex-wrap items-center gap-1">
              <Badge
                variant="outline"
                className="max-w-full truncate border-primary/40 bg-primary/10 px-1.5 py-0 text-[10px] font-medium"
                title={primary.via}
              >
                {primary.via}
              </Badge>
              {extraReasons > 0 && (
                <span className="text-[10px] text-muted-foreground">
                  {t('works_with.more', { count: extraReasons })}
                </span>
              )}
            </div>
          )}
        </div>
      </Link>
    </li>
  )
}

function RowSkeleton() {
  return (
    <div className="flex items-center gap-3 rounded-md border border-border bg-card p-2">
      <div className="h-10 w-10 shrink-0 rounded bg-muted" />
      <div className="flex flex-1 flex-col gap-1.5">
        <div className="h-3 w-2/3 rounded bg-muted" />
        <div className="h-3 w-1/3 rounded bg-muted" />
      </div>
    </div>
  )
}

/**
 * "Works with" — for the currently-open hyperobject, lists every other
 * catalogued object it physically interfaces with (shared real standards like
 * NEMA / VESA / Gridfinity / 1/4-20). Clicking a partner opens that object.
 *
 * Consumes GET /api/catalog/<slug>/works-with. Never throws into its parent:
 * loading / error / empty states are all rendered inline.
 */
export default function WorksWithPanel({ slug }: WorksWithPanelProps) {
  const { t } = useLanguage()
  const [state, setState] = useState<LoadState>('loading')
  const [count, setCount] = useState(0)
  const [partners, setPartners] = useState<WorksWithPartner[]>([])
  // Bumped by retry to force the fetch effect to re-run for the same slug.
  const [reloadNonce, setReloadNonce] = useState(0)

  // Fetch companions whenever the slug (or an explicit retry) changes. This
  // synchronizes React with the external catalog API; the leading reset to
  // 'loading' is intentional so the skeleton shows immediately on slug change
  // and retry (same intentional pattern as ProjectsView's primary fetch).
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    let cancelled = false
    setState('loading')
    apiFetch(`${getApiBase()}/api/catalog/${slug}/works-with`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: WorksWithResponse) => {
        if (cancelled) return
        setPartners(Array.isArray(data.partners) ? data.partners : [])
        setCount(typeof data.count === 'number' ? data.count : 0)
        setState('loaded')
      })
      .catch(() => {
        if (cancelled) return
        setState('error')
      })
    return () => {
      cancelled = true
    }
  }, [slug, reloadNonce])
  /* eslint-enable react-hooks/set-state-in-effect */

  const retry = useCallback(() => setReloadNonce((n) => n + 1), [])

  const subtitle =
    count === 1
      ? t('works_with.subtitle_one', { count })
      : t('works_with.subtitle', { count })

  return (
    <section aria-labelledby="works-with-heading" className="space-y-2">
      <div>
        {/* h2 to match the sidebar's section-heading level and avoid a heading-order
            skip in the full page (axe heading-order: levels must increase by one). */}
        <h2
          id="works-with-heading"
          className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground"
        >
          <Link2 className="h-3.5 w-3.5" aria-hidden="true" />
          {t('works_with.title')}
        </h2>
        {state === 'loaded' && count > 0 && (
          <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
        )}
      </div>

      {state === 'loading' && (
        <div className="space-y-2" aria-busy="true">
          <span className="sr-only">{t('works_with.loading')}</span>
          {Array.from({ length: 3 }).map((_, i) => (
            <RowSkeleton key={i} />
          ))}
        </div>
      )}

      {state === 'error' && (
        <div className="flex flex-col items-start gap-2 rounded-md border border-border bg-muted/40 p-3">
          <p className="text-xs text-muted-foreground">{t('works_with.error')}</p>
          <Button variant="outline" size="sm" className="h-7 text-xs" onClick={retry}>
            {t('works_with.retry')}
          </Button>
        </div>
      )}

      {state === 'loaded' && count === 0 && (
        <p className="rounded-md border border-dashed border-border bg-muted/30 p-3 text-xs leading-relaxed text-muted-foreground">
          {t('works_with.empty')}
        </p>
      )}

      {state === 'loaded' && count > 0 && (
        <ul className="space-y-2">
          {partners.map((partner) => (
            <PartnerRow key={partner.slug} partner={partner} t={t} />
          ))}
        </ul>
      )}
    </section>
  )
}
